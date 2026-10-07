"""Python 2 Behavior Capture Module — CONTRACTS.md § CaptureRecord.

Executes a Python 2 module entry point with type-tagged inputs in the Python 2 sandbox.
Captures observable behaviors:
  - type-tagged return values
  - exceptions as structured data {"class": ..., "message": ...}
  - stdout / stderr streams (with truncation markers for large outputs)
  - execution duration in ms
  - 3 runs for determinism checking (marking non-determinism with reason)
  - side-effect detection (time, random, file I/O, network, environment variables, global state mutation)
  - lossy serialization marking (tagged repr_fallback)
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from parity.contracts import CaptureRecord
from parity.sandbox import SandboxResult, run_sandboxed
from parity.serializer import (
    SerializationError,
    is_tagged_value,
    make_tagged,
    validate_tagged_value,
)

MAX_OUTPUT_CHARS = 10000  # Truncation bound
TRUNCATION_MARKER = "\n... [TRUNCATED: OUTPUT EXCEEDED 10000 CHARACTERS] ...\n"


def _truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> Tuple[str, bool]:
    """Truncate huge stdout/stderr with an explicit marker."""
    if len(text) > max_chars:
        truncated = text[:max_chars] + TRUNCATION_MARKER
        return truncated, True
    return text, False


def _detect_static_side_effects(source_code: str, entry_point_name: Optional[str] = None) -> Dict[str, bool]:
    """Inspect AST and regex patterns in Python 2 module code for side effect primitives."""
    flags = {
        "time": False,
        "random": False,
        "file_io": False,
        "network": False,
        "env": False,
        "global_state": False,
    }

    try:
        tree = ast.parse(source_code)
    except Exception:
        # Fallback to lexical pattern checks if syntax parsing fails
        tree = None

    # Check for random usage
    if re.search(r'\b(random|randint|choice|shuffle|uniform|sample|randrange)\b', source_code):
        flags["random"] = True

    # Check for time usage
    if re.search(r'\b(time\.time|time\.clock|datetime\.now|time\.sleep|time\.gmtime|time\.localtime)\b', source_code):
        flags["time"] = True

    # Check for file I/O
    if re.search(r'\b(open\s*\(|file\s*\(|os\.remove|os\.unlink|os\.mkdir|os\.rename|shutil\.)', source_code):
        flags["file_io"] = True

    # Check for network usage
    if re.search(r'\b(urllib|urllib2|socket|http|requests|httplib|ftp|telnet)\b', source_code):
        flags["network"] = True

    # Check for environment variables
    if re.search(r'\b(os\.environ|os\.getenv|os\.putenv)\b', source_code):
        flags["env"] = True

    # Check for global state mutation (AST search for `global` keyword or module-level assignments inside functions)
    if tree:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if entry_point_name is None or node.name == entry_point_name:
                    for child in ast.walk(node):
                        if isinstance(child, ast.Global):
                            flags["global_state"] = True

    if re.search(r'\bglobal\s+[a-zA-Z_]', source_code):
        flags["global_state"] = True

    return flags


def _generate_harness_script(
    module_code: str,
    entry_point: str,
    serialized_input: Dict[str, Any],
) -> str:
    """Generate Python 2 runner script that executes entry_point(args, kwargs) and encodes output to JSON."""
    
    # Injected helper code to run the entry point, capture stdout/stderr, return, and exception
    harness = f"""
import sys, io, json, os, time

# --- Module Code ---
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
        b_val = bytes(v) if isinstance(v, (bytes, bytearray)) else str(v).encode('latin-1')
        try:
            return _Py2Bytes(b_val)
        except NameError:
            return b_val
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
    elif isinstance(val, (int,)):
        # If integer bit length exceeds 63 in Py2, it acts as long
        if abs(val) > 0x7FFFFFFFFFFFFFFF:
            return {{'t': 'long', 'v': val}}, False
        return {{'t': 'int', 'v': val}}, False
    elif isinstance(val, float):
        return {{'t': 'float', 'v': val}}, False
    elif isinstance(val, bytes):
        return {{'t': 'str', 'v': val.decode('latin-1')}}, False
    elif isinstance(val, str):
        return {{'t': 'str', 'v': val}}, False
    elif isinstance(val, (list,)):
        encoded_list = []
        is_lossy = False
        for item in val:
            enc, l = __encode_tagged(item)
            encoded_list.append(enc)
            if l: is_lossy = True
        return {{'t': 'list', 'v': encoded_list}}, is_lossy
    elif isinstance(val, (tuple,)):
        encoded_tuple = []
        is_lossy = False
        for item in val:
            enc, l = __encode_tagged(item)
            encoded_tuple.append(enc)
            if l: is_lossy = True
        return {{'t': 'tuple', 'v': encoded_tuple}}, is_lossy
    elif isinstance(val, (dict,)):
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
        # Repr fallback for unhandled objects
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


def capture_behavior(
    module_path: Union[str, Path],
    entry_point: str,
    serialized_input: Dict[str, Any],
    timeout_sec: float = 5.0,
    runs: int = 3,
) -> CaptureRecord:
    """Execute entry_point in the Python 2 sandbox 3 times to produce a CaptureRecord.
    
    Detects non-determinism, side effects, output truncation, and lossy serialization.
    """
    p = Path(module_path)
    module_name = p.stem
    if not p.exists():
        raise FileNotFoundError(f"Module file not found: {module_path}")

    module_code = p.read_text(encoding="utf-8")
    harness_code = _generate_harness_script(module_code, entry_point, serialized_input)

    # Initial static analysis of side effects
    side_effects = _detect_static_side_effects(module_code, entry_point)

    run_outputs = []
    durations = []
    is_lossy = False

    for run_idx in range(runs):
        res: SandboxResult = run_sandboxed(harness_code, python_version="2", timeout_sec=timeout_sec)
        durations.append(res.duration_ms)

        stdout_raw = res.stdout
        # Extract payload between JSON start/end markers
        match = re.search(r'__PARITY_CAPTURE_JSON_START__(.*?)__PARITY_CAPTURE_JSON_END__', stdout_raw, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(1))
                ret_val = payload["return"]
                exc_val = payload["exception"]
                captured_stdout = payload.get("stdout", "")
                captured_stderr = payload.get("stderr", "")
                if payload.get("lossy", False):
                    is_lossy = True
            except Exception as e:
                ret_val = make_tagged("none", None)
                exc_val = make_tagged("exception", {"class": "JSONDecodeError", "message": str(e)})
                captured_stdout = stdout_raw
                captured_stderr = res.stderr
        else:
            # Fallback if runner itself failed before harness printed JSON
            ret_val = make_tagged("none", None)
            if res.exception_type:
                exc_val = make_tagged("exception", {"class": res.exception_type, "message": res.exception_message or ""})
            else:
                exc_val = make_tagged("none", None)
            captured_stdout = res.stdout
            captured_stderr = res.stderr

        # Truncate large stdout / stderr
        trunc_stdout, t1 = _truncate_output(captured_stdout)
        trunc_stderr, t2 = _truncate_output(captured_stderr)

        outputs_record = {
            "return": ret_val,
            "exception": exc_val,
            "stdout": trunc_stdout,
            "stderr": trunc_stderr,
        }
        run_outputs.append(outputs_record)

    # Check determinism across runs
    deterministic = True
    non_determinism_reason = None

    first = run_outputs[0]
    for idx, subsequent in enumerate(run_outputs[1:], start=2):
        if first["return"] != subsequent["return"]:
            deterministic = False
            non_determinism_reason = f"Return value diverged on run {idx}: {first['return']} != {subsequent['return']}"
            break
        elif first["exception"] != subsequent["exception"]:
            deterministic = False
            non_determinism_reason = f"Exception diverged on run {idx}: {first['exception']} != {subsequent['exception']}"
            break
        elif first["stdout"] != subsequent["stdout"]:
            deterministic = False
            non_determinism_reason = f"Stdout output diverged on run {idx}"
            break
        elif first["stderr"] != subsequent["stderr"]:
            deterministic = False
            non_determinism_reason = f"Stderr output diverged on run {idx}"
            break

    # If non-deterministic, flag random/time side-effects
    if not deterministic:
        if side_effects["random"]:
            non_determinism_reason = (non_determinism_reason or "") + " (module uses random/pseudo-randomness)"
        if side_effects["time"]:
            non_determinism_reason = (non_determinism_reason or "") + " (module accesses dynamic clock/time)"

    avg_duration_ms = sum(durations) / len(durations) if durations else 0.0

    record = CaptureRecord(
        module=module_name,
        entry_point=entry_point,
        input=serialized_input,
        outputs=run_outputs[0],
        duration_ms=avg_duration_ms,
        runs=runs,
        deterministic=deterministic,
        non_determinism_reason=non_determinism_reason,
        side_effect_flags=side_effects,
        lossy=is_lossy,
    )
    return record
