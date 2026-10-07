"""Differential Verifier — CONTRACTS.md § Comparator rules (R1 to R6) and § Divergence.

For each captured input on a Python 2 module, runs the migrated Python 3 module
in the Python 3 sandbox and compares the observable behavior against the recorded
Python 2 behavior.

Implements rules R1–R6:
  - R1: str/unicode/str3 text equality (equal only if decoded text is identical; bytes vs text NEVER equal)
  - R2: int vs long (equal if numerically equal)
  - R3: floats (equal within configured tolerance, default exact)
  - R4: dict/set ordering (compare as sets/maps, flag order-dependent if output text depends on order)
  - R5: exception (class name AND message must match unless explicitly mapped in config)
  - R6: timing differences alone never count as divergence; reported separately

Default stance: when a rule is unclear or non-coercible, count it as a divergence (fail closed).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from parity.config import ComparatorConfig, PARITYConfig
from parity.contracts import CaptureRecord, Divergence
from parity.sandbox import SandboxResult, run_sandboxed
from parity.serializer import make_tagged


def _generate_py3_harness_script(
    module_code: str,
    entry_point: str,
    serialized_input: Dict[str, Any],
) -> str:
    """Generate Python 3 runner harness executing entry_point(args, kwargs) and returning type-tagged JSON."""
    harness = f"""
import sys, io, json, os, time

# --- Migrated Python 3 Module Code ---
{module_code}

# --- Invocation Harness ---
__input_data = {json.dumps(serialized_input)}

def __decode_tagged(tagged):
    if not isinstance(tagged, dict) or 't' not in tagged:
        return tagged
    t = tagged['t']
    v = tagged.get('v')
    if t == 'none':
        return None
    elif t == 'bool':
        return bool(v)
    elif t in ('int', 'long'):
        return int(v)
    elif t == 'float':
        return float(v)
    elif t in ('str', 'unicode', 'str3'):
        return str(v)
    elif t == 'bytes3':
        return bytes(v) if isinstance(v, (bytes, bytearray)) else str(v).encode('latin-1')
    elif t == 'list':
        return [__decode_tagged(item) for item in v]
    elif t == 'tuple':
        return tuple(__decode_tagged(item) for item in v)
    elif t == 'dict':
        d = {{}}
        for pair in v:
            d[__decode_tagged(pair[0])] = __decode_tagged(pair[1])
        return d
    elif t == 'set':
        items = v.get('items', []) if isinstance(v, dict) else v
        return set(__decode_tagged(x) for x in items)
    return v

def __encode_tagged(val):
    if val is None:
        return {{'t': 'none', 'v': None}}, False
    elif isinstance(val, bool):
        return {{'t': 'bool', 'v': val}}, False
    elif isinstance(val, int):
        return {{'t': 'int', 'v': val}}, False
    elif isinstance(val, float):
        return {{'t': 'float', 'v': val}}, False
    elif isinstance(val, bytes):
        return {{'t': 'bytes3', 'v': val.decode('latin-1')}}, False
    elif isinstance(val, str):
        return {{'t': 'str3', 'v': val}}, False
    elif isinstance(val, list):
        encoded_list = []
        is_lossy = False
        for item in val:
            enc, l = __encode_tagged(item)
            encoded_list.append(enc)
            if l: is_lossy = True
        return {{'t': 'list', 'v': encoded_list}}, is_lossy
    elif isinstance(val, tuple):
        encoded_tuple = []
        is_lossy = False
        for item in val:
            enc, l = __encode_tagged(item)
            encoded_tuple.append(enc)
            if l: is_lossy = True
        return {{'t': 'tuple', 'v': encoded_tuple}}, is_lossy
    elif isinstance(val, dict):
        pairs = []
        is_lossy = False
        for k, v in val.items():
            k_enc, kl = __encode_tagged(k)
            v_enc, vl = __encode_tagged(v)
            pairs.append([k_enc, v_enc])
            if kl or vl: is_lossy = True
        return {{'t': 'dict', 'v': pairs}}, is_lossy
    elif isinstance(val, (set, frozenset)):
        items = []
        is_lossy = False
        for item in sorted(list(val), key=lambda x: str(x)):
            enc, l = __encode_tagged(item)
            items.append(enc)
            if l: is_lossy = True
        return {{'t': 'set', 'v': {{'items': items, 'ordered_by': 'repr'}}}}, is_lossy
    else:
        return {{'t': 'repr_fallback', 'v': repr(val)}}, True

__stdout_buf = io.StringIO()
__stderr_buf = io.StringIO()
__old_stdout, __old_stderr = sys.stdout, sys.stderr
sys.stdout, sys.stderr = __stdout_buf, __stderr_buf

__ret_val = None
__exc_info = None
__is_lossy = False

try:
    __fn = globals().get({json.dumps(entry_point)})
    if __fn is None:
        raise AttributeError("Entry point '" + {json.dumps(entry_point)} + "' not found in module")
    
    __args_data = __input_data.get('args', [])
    __kwargs_data = __input_data.get('kwargs', {{}})
    
    __decoded_args = [__decode_tagged(a) for a in __args_data]
    __decoded_kwargs = {{k: __decode_tagged(v) for k, v in __kwargs_data.items()}}
    
    __ret_val = __fn(*__decoded_args, **__decoded_kwargs)
except Exception as __e:
    __exc_info = {{
        "class": type(__e).__name__,
        "message": str(__e)
    }}

sys.stdout, sys.stderr = __old_stdout, __old_stderr

if __exc_info is not None:
    __enc_ret = {{'t': 'none', 'v': None}}
    __enc_exc = {{'t': 'exception', 'v': __exc_info}}
else:
    __enc_ret, __is_lossy = __encode_tagged(__ret_val)
    __enc_exc = {{'t': 'none', 'v': None}}

__out_payload = {{
    "return": __enc_ret,
    "exception": __enc_exc,
    "stdout": __stdout_buf.getvalue(),
    "stderr": __stderr_buf.getvalue(),
    "lossy": __is_lossy
}}

print("__PARITY_CAPTURE_JSON_START__" + json.dumps(__out_payload) + "__PARITY_CAPTURE_JSON_END__")
"""
    return harness


def compare_tagged_values(
    py2_val: Dict[str, Any],
    py3_val: Dict[str, Any],
    config: ComparatorConfig,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Compare type-tagged values according to rules R1–R4.
    
    Returns (matches, applied_rule, failure_category).
    """
    t2, v2 = py2_val.get("t"), py2_val.get("v")
    t3, v3 = py3_val.get("t"), py3_val.get("v")

    # None check
    if t2 == "none" and t3 == "none":
        return True, "None equality", None

    # R1: str / unicode / str3 text equality (bytes vs text is NEVER equal)
    if t2 in ("str", "unicode") and t3 == "str3":
        if v2 == v3:
            return True, "R1: text equality", None
        return False, "R1: text equality", "value"
    if t2 == "str" and t3 == "bytes3":
        # Py2 str vs Py3 bytes3 is NEVER equal per R1
        return False, "R1: bytes vs text inequality", "type"

    # R2: int vs long equality (equal if numerically equal)
    if t2 in ("int", "long") and t3 in ("int", "long"):
        if v2 == v3:
            return True, "R2: int/long numeric equality", None
        return False, "R2: int/long numeric equality", "numeric"

    # R3: float equality
    if (t2 == "float" and t3 == "float") or (t2 in ("int", "long", "float") and t3 in ("int", "long", "float")):
        if t2 == t3 == "float":
            if abs(v2 - v3) <= config.float_tolerance:
                return True, "R3: float tolerance", None
            return False, "R3: float tolerance", "numeric"
        elif (t2 in ("int", "long") and t3 == "float") or (t2 == "float" and t3 in ("int", "long")):
            return False, "R3: int vs float type mismatch", "type"

    # Booleans
    if t2 == "bool" and t3 == "bool":
        if v2 == v3:
            return True, "Boolean equality", None
        return False, "Boolean equality", "value"

    # Lists / Tuples
    if t2 in ("list", "tuple") and t3 in ("list", "tuple"):
        if t2 != t3:
            return False, "Sequence type mismatch", "type"
        if len(v2) != len(v3):
            return False, "Sequence length mismatch", "value"
        for i, (item2, item3) in enumerate(zip(v2, v3)):
            matches, rule, cat = compare_tagged_values(item2, item3, config)
            if not matches:
                return False, f"Sequence item {i}: {rule}", cat
        return True, "Sequence element equality", None

    # R4: dict ordering / mapping comparison
    if t2 == "dict" and t3 == "dict":
        # Convert pairs list to dicts keyed by decoded string/repr for set comparison
        if len(v2) != len(v3):
            return False, "R4: dict size mismatch", "value"
        # Compare key-value maps
        d2 = {json.dumps(k, sort_keys=True): v for k, v in v2}
        d3 = {json.dumps(k, sort_keys=True): v for k, v in v3}
        if set(d2.keys()) != set(d3.keys()):
            return False, "R4: dict keys mismatch", "value"
        for k_str, val2 in d2.items():
            val3 = d3[k_str]
            matches, rule, cat = compare_tagged_values(val2, val3, config)
            if not matches:
                return False, f"R4 dict value for {k_str}: {rule}", cat
        return True, "R4: dict map equality", None

    # R4: set comparison
    if t2 == "set" and t3 == "set":
        items2 = v2.get("items", []) if isinstance(v2, dict) else v2
        items3 = v3.get("items", []) if isinstance(v3, dict) else v3
        s2 = {json.dumps(x, sort_keys=True) for x in items2}
        s3 = {json.dumps(x, sort_keys=True) for x in items3}
        if s2 == s3:
            return True, "R4: set element equality", None
        return False, "R4: set elements mismatch", "value"

    # Default fallback: exact tag and value match
    if t2 == t3 and v2 == v3:
        return True, "Exact match", None

    return False, "Default strict divergence", "type" if t2 != t3 else "value"


def verify_differential(
    capture_record: CaptureRecord,
    migrated_py3_code: str,
    config: Optional[PARITYConfig] = None,
    timeout_sec: float = 5.0,
) -> Tuple[bool, List[Divergence], Dict[str, Any]]:
    """Run migrated Python 3 code on captured input and compare against recorded Py2 behavior.
    
    Returns (is_parity, divergences_list, py3_observed_behavior).
    """
    if config is None:
        config = PARITYConfig()
    comp_config = config.comparator

    harness = _generate_py3_harness_script(
        module_code=migrated_py3_code,
        entry_point=capture_record.entry_point,
        serialized_input=capture_record.input,
    )

    res_py3: SandboxResult = run_sandboxed(harness, python_version="3", timeout_sec=timeout_sec)

    # Extract observed Py3 outputs
    match = re.search(r'__PARITY_CAPTURE_JSON_START__(.*?)__PARITY_CAPTURE_JSON_END__', res_py3.stdout, re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(1))
            py3_ret = payload["return"]
            py3_exc = payload["exception"]
            py3_stdout = payload.get("stdout", "")
            py3_stderr = payload.get("stderr", "")
        except Exception:
            py3_ret = make_tagged("none", None)
            py3_exc = make_tagged("exception", {"class": "JSONDecodeError", "message": "Failed decoding runner JSON"})
            py3_stdout = res_py3.stdout
            py3_stderr = res_py3.stderr
    else:
        py3_ret = make_tagged("none", None)
        if res_py3.exception_type:
            py3_exc = make_tagged("exception", {"class": res_py3.exception_type, "message": res_py3.exception_message or ""})
        else:
            py3_exc = make_tagged("none", None)
        py3_stdout = res_py3.stdout
        py3_stderr = res_py3.stderr

    py3_observed = {
        "return": py3_ret,
        "exception": py3_exc,
        "stdout": py3_stdout,
        "stderr": py3_stderr,
        "exit_code": res_py3.exit_code,
        "duration_ms": res_py3.duration_ms,
    }

    py2_outputs = capture_record.outputs
    divergences: List[Divergence] = []

    # 1. Compare Exceptions (R5)
    py2_exc = py2_outputs.get("exception", {})
    py2_has_exc = py2_exc.get("t") == "exception"
    py3_has_exc = py3_exc.get("t") == "exception"

    if py2_has_exc != py3_has_exc:
        divergences.append(Divergence(
            module=capture_record.module,
            entry_point=capture_record.entry_point,
            input=capture_record.input,
            py2_behavior=py2_outputs,
            py3_behavior=py3_observed,
            category="exception_type" if py3_has_exc else "value",
            comparator_rule_applied="R5: Exception occurrence mismatch",
            severity="high",
        ))
    elif py2_has_exc and py3_has_exc:
        # Both raised exceptions: check class and message
        py2_info = py2_exc.get("v", {})
        py3_info = py3_exc.get("v", {})
        c2 = py2_info.get("class")
        c3 = py3_info.get("class")
        # Check mapping
        mapped_c2 = comp_config.exception_class_mapping.get(c2, c2)
        if mapped_c2 != c3:
            divergences.append(Divergence(
                module=capture_record.module,
                entry_point=capture_record.entry_point,
                input=capture_record.input,
                py2_behavior=py2_outputs,
                py3_behavior=py3_observed,
                category="exception_type",
                comparator_rule_applied="R5: Exception class mapping",
                severity="high",
            ))
        elif py2_info.get("message") != py3_info.get("message"):
            divergences.append(Divergence(
                module=capture_record.module,
                entry_point=capture_record.entry_point,
                input=capture_record.input,
                py2_behavior=py2_outputs,
                py3_behavior=py3_observed,
                category="exception_message",
                comparator_rule_applied="R5: Exception message mismatch",
                severity="low",
            ))

    # 2. Compare Return Values (R1–R4) if no exception occurred
    if not py2_has_exc and not py3_has_exc:
        py2_ret = py2_outputs.get("return", {})
        matches, rule_applied, cat = compare_tagged_values(py2_ret, py3_ret, comp_config)
        if not matches:
            divergences.append(Divergence(
                module=capture_record.module,
                entry_point=capture_record.entry_point,
                input=capture_record.input,
                py2_behavior=py2_outputs,
                py3_behavior=py3_observed,
                category=cat or "value",
                comparator_rule_applied=rule_applied or "Strict divergence",
                severity="high",
            ))

    # 3. Compare Stdout (R1/R4)
    if py2_outputs.get("stdout", "").strip() != py3_stdout.strip():
        # Check if difference is purely dict ordering in stdout
        divergences.append(Divergence(
            module=capture_record.module,
            entry_point=capture_record.entry_point,
            input=capture_record.input,
            py2_behavior=py2_outputs,
            py3_behavior=py3_observed,
            category="stdout",
            comparator_rule_applied="R1/R4: Stdout divergence",
            severity="low" if not py2_has_exc else "high",
        ))

    is_parity = len(divergences) == 0
    return is_parity, divergences, py3_observed
