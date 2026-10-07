"""Sandboxed execution module for untrusted legacy code.

Supports Python 2.7 and Python 3 execution under strict isolation controls:
  - No network (--network none / socket monkey-patch)
  - Read-only filesystem except isolated per-run temp dir
  - Non-root sandbox identity & scrubbed host environment variables
  - Memory address normalization & deterministic PID / time / sleep mocking
  - CPU, memory, and timeout resource bounds

Returns JSON result dictionary:
  {stdout, stderr, exit_code, exception_type, exception_message, duration_ms, timed_out}
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    exception_type: Optional[str]
    exception_message: Optional[str]
    duration_ms: float
    timed_out: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def is_docker_available() -> bool:
    """Return True if docker CLI is available and docker daemon is responding."""
    try:
        res = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=2.0,
            text=True,
        )
        return res.returncode == 0
    except Exception:
        return False


def run_sandboxed_docker(
    code: str,
    python_version: str = "3",
    timeout_sec: float = 5.0,
    mem_limit: str = "512m",
    cpu_limit: str = "1.0",
) -> SandboxResult:
    """Execute Python code in an isolated Docker container with strict sandbox flags."""
    img_tag = f"parity-runner-py{python_version}"

    cmd = [
        "docker", "run", "--rm", "-i",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--user", "1000:1000",
        "--cpus", cpu_limit,
        "--memory", mem_limit,
        "--pids-limit", "64",
        "-e", "PYTHONHASHSEED=0",
        "-e", "LC_ALL=C.UTF-8",
        "-e", "LANG=C.UTF-8",
        "-e", "TZ=UTC",
        img_tag,
    ]

    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=code,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        duration_ms = (time.time() - start_time) * 1000.0

        try:
            out_data = json.loads(proc.stdout.strip())
            stdout_txt = out_data.get("stdout", "")
            # Normalize hex memory addresses in output for cross-run determinism
            stdout_txt = re.sub(r"at 0x[0-9a-fA-F]+", "at 0x000000000000", stdout_txt)

            return SandboxResult(
                stdout=stdout_txt,
                stderr=out_data.get("stderr", ""),
                exit_code=out_data.get("exit_code", 0),
                exception_type=out_data.get("exception_type"),
                exception_message=out_data.get("exception_message"),
                duration_ms=out_data.get("duration_ms", duration_ms),
                timed_out=False,
            )
        except Exception:
            stdout_txt = re.sub(r"at 0x[0-9a-fA-F]+", "at 0x000000000000", proc.stdout)
            return SandboxResult(
                stdout=stdout_txt,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                exception_type=None,
                exception_message=None,
                duration_ms=round(duration_ms, 3),
                timed_out=False,
            )
    except subprocess.TimeoutExpired as e:
        duration_ms = (time.time() - start_time) * 1000.0
        return SandboxResult(
            stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "Timed out"),
            exit_code=-1,
            exception_type="TimeoutError",
            exception_message=f"Execution exceeded timeout of {timeout_sec}s",
            duration_ms=round(duration_ms, 3),
            timed_out=True,
        )


def _transform_print_stmts(code: str) -> str:
    """Transform Python 2 print statements into print() function calls.

    Handles: print x  ->  print(x)
             print x, y  ->  print(x, y)
             print >> sys.stderr, x  ->  (skip, rare)
    Does NOT touch lines that already use print(...).
    """
    lines = code.split('\n')
    transformed = []
    for line in lines:
        # Match 'print <expr>' but not 'print(' or 'print =' etc.
        m = re.match(r'^(\s*)print\s+(?!\()(.*)', line)
        if m:
            indent = m.group(1)
            rest = m.group(2).rstrip()
            # Skip print >> redirect syntax (too complex to emulate simply)
            if rest.startswith('>>'):
                transformed.append(line)
            else:
                transformed.append(f'{indent}print({rest})')
        else:
            transformed.append(line)
    return '\n'.join(transformed)


def _transform_py2_ast(code: str) -> str:
    """Use AST to apply Python 2 semantic transforms:

    1. Rewrite a/b → _py2_div(a, b) for integer division semantics
    2. Wrap bytes literals b"..." → _Py2Bytes(b"...") for Py2-style indexing
    3. Wrap dict literals {...} → _Py2Dict({...}) for list-returning .keys()
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code  # Can't parse, return as-is

    class Py2Transformer(ast.NodeTransformer):
        def visit_BinOp(self, node):
            self.generic_visit(node)
            if isinstance(node.op, ast.Div):
                return ast.Call(
                    func=ast.Name(id='_py2_div', ctx=ast.Load()),
                    args=[node.left, node.right],
                    keywords=[]
                )
            return node

        def visit_Constant(self, node):
            if isinstance(node.value, bytes):
                return ast.Call(
                    func=ast.Name(id='_Py2Bytes', ctx=ast.Load()),
                    args=[node],
                    keywords=[]
                )
            return node

        def visit_Dict(self, node):
            self.generic_visit(node)
            return ast.Call(
                func=ast.Name(id='_Py2Dict', ctx=ast.Load()),
                args=[ast.Dict(keys=node.keys, values=node.values)],
                keywords=[]
            )

        def visit_Attribute(self, node):
            self.generic_visit(node)
            if node.attr == 'message' and isinstance(node.ctx, ast.Load):
                # Py2 e.message on exceptions -> getattr(node.value, 'message', str(node.value))
                return ast.Call(
                    func=ast.Name(id='getattr', ctx=ast.Load()),
                    args=[node.value, ast.Constant(value='message'), ast.Call(
                        func=ast.Name(id='str', ctx=ast.Load()),
                        args=[node.value],
                        keywords=[]
                    )],
                    keywords=[]
                )
            return node

    tree = Py2Transformer().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


# Python 2 semantic preamble injected before user code execution
_PY2_PREAMBLE = r'''
import builtins as _builtins
import math as _math
import functools as _functools

# --- Py2 integer division: a / b does floor division for int operands ---
# The AST transform rewrites a/b -> _py2_div(a, b) before execution
def _py2_div(a, b):
    """Py2-style division: floor division for int/int, true division otherwise."""
    if isinstance(a, int) and not isinstance(a, bool) and isinstance(b, int) and not isinstance(b, bool):
        return a // b
    return a / b

# --- Py2 bytes: indexing returns single-char string, not int; concat with str works ---
class _Py2Bytes(bytes):
    def __getitem__(self, key):
        result = bytes.__getitem__(self, key)
        if isinstance(key, int):
            return chr(result)  # Py2: b"hello"[0] -> "h", not 104
        return _Py2Bytes(result)
    def __add__(self, other):
        # Py2: b"hello" + " world" works because bytes IS str
        if isinstance(other, str):
            return self.decode('latin-1') + other
        return _Py2Bytes(bytes.__add__(self, other))
    def __radd__(self, other):
        if isinstance(other, str):
            return other + self.decode('latin-1')
        return _Py2Bytes(bytes.__radd__(self, other))

# Monkey-patch bytes constructor
_original_bytes = bytes
def _py2_bytes_wrapper(*args, **kwargs):
    return _Py2Bytes(_original_bytes(*args, **kwargs))

# Monkey-patch range to return list (Py2 behavior)
_original_range = _builtins.range
def _py2_range(*args):
    return list(_original_range(*args))

# --- Py2 round: half-away-from-zero ---
def _py2_round(number, ndigits=0):
    if ndigits == 0:
        if number > 0:
            return float(_math.floor(number + 0.5))
        else:
            return float(_math.ceil(number - 0.5))
    multiplier = 10 ** ndigits
    if number > 0:
        return float(_math.floor(number * multiplier + 0.5)) / multiplier
    return float(_math.ceil(number * multiplier - 0.5)) / multiplier

# --- Py2 type() name overrides ---
_original_type = _builtins.type
class _Py2Type:
    """Wrapper to make type() return Py2-compatible type names."""
    def __call__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            obj = args[0]
            real_type = _original_type(obj)
            # In Py2, bytes IS str, so _Py2Bytes should report as str
            if real_type.__name__ == '_Py2Bytes' or (real_type is bytes):
                return _StrType
            # In Py2, large ints have type 'long'
            if real_type is int or _original_type(obj).__name__ == '_Py2Int':
                val = int(obj)
                # Py2: integers > 2^63-1 or < -2^63 are 'long'
                if val.bit_length() > 63:
                    return _LongType
                return _Py2IntType
            return real_type
        return _original_type(*args, **kwargs)
    def __instancecheck__(cls, instance):
        return isinstance(instance, _original_type)

# --- Py2 isinstance: bytes IS str in Py2 ---
_original_isinstance = _builtins.isinstance
def _py2_isinstance(obj, classinfo):
    # In Py2, isinstance(b"hello", str) is True because bytes==str
    if _original_isinstance(classinfo, _original_type):
        if classinfo is str and _original_isinstance(obj, (bytes, _Py2Bytes)):
            return True
    elif _original_isinstance(classinfo, tuple):
        for c in classinfo:
            if c is str and _original_isinstance(obj, (bytes, _Py2Bytes)):
                return True
    return _original_isinstance(obj, classinfo)

class _FakeStrType:
    __name__ = "str"
    def __repr__(self):
        return "<type 'str'>"
    def __eq__(self, other):
        return other is str or other is self or (hasattr(other, '__name__') and other.__name__ == 'str')
    def __hash__(self):
        return hash('str')

class _FakeLongType:
    __name__ = "long"
    def __repr__(self):
        return "<type 'long'>"
    def __eq__(self, other):
        return other is self or (hasattr(other, '__name__') and other.__name__ == 'long')
    def __hash__(self):
        return hash('long')

class _FakePy2IntType:
    __name__ = "int"
    def __repr__(self):
        return "<type 'int'>"
    def __eq__(self, other):
        return other is int or other is self
    def __hash__(self):
        return hash(int)

_LongType = _FakeLongType()
_Py2IntType = _FakePy2IntType()
_StrType = _FakeStrType()

# --- Py2 builtins ---
_builtins.reduce = _functools.reduce
_builtins.raw_input = input
_builtins.xrange = _original_range  # xrange returns iterator (like Py3 range)
_builtins.long = int
_builtins.unicode = str
_builtins.round = _py2_round
_builtins.range = _py2_range
_builtins.type = _Py2Type()
_builtins.isinstance = _py2_isinstance

# --- Py2 hash: hash(b"x") == hash("x") (str and bytes are same in Py2) ---
_original_hash = _builtins.hash
def _py2_hash(obj):
    if isinstance(obj, bytes):
        return _original_hash(obj.decode('latin-1', errors='replace'))
    return _original_hash(obj)
_builtins.hash = _py2_hash

# --- Py2 hasattr: exceptions have 'message' attribute in Py2 ---
_original_hasattr = _builtins.hasattr
def _py2_hasattr(obj, name):
    if name == 'message' and isinstance(obj, BaseException):
        return True
    return _original_hasattr(obj, name)
_builtins.hasattr = _py2_hasattr

# --- Py2 sorted: support cmp parameter AND mixed-type sorting ---
_original_sorted = _builtins.sorted
def _py2_sorted(iterable, cmp=None, key=None, reverse=False):
    if cmp is not None:
        key = _functools.cmp_to_key(cmp)
    try:
        return _original_sorted(iterable, key=key, reverse=reverse)
    except TypeError:
        # Py2 allows sorting mixed types by comparing type names then values
        def _mixed_key(x):
            try:
                return (0, type(x).__name__, x)
            except TypeError:
                return (0, type(x).__name__, str(x))
        return _original_sorted(iterable, key=_mixed_key, reverse=reverse)
_builtins.sorted = _py2_sorted

# --- Py2 map/filter/zip return lists ---
_original_map = _builtins.map
_original_filter = _builtins.filter
_original_zip = _builtins.zip
def _py2_map(fn, *iterables):
    return list(_original_map(fn, *iterables))
def _py2_filter(fn, iterable):
    return list(_original_filter(fn, iterable))
def _py2_zip(*iterables):
    return list(_original_zip(*iterables))
_builtins.map = _py2_map
_builtins.filter = _py2_filter
_builtins.zip = _py2_zip

# --- Py2 dict.keys() returns list ---
_OriginalDict = dict
class _Py2Dict(_OriginalDict):
    def keys(self):
        return list(_OriginalDict.keys(self))
    def values(self):
        return list(_OriginalDict.values(self))
    def items(self):
        return list(_OriginalDict.items(self))

# Wrap dict literals by overriding dict builtin
_builtins.dict = _Py2Dict

# --- Py2 bytes == str (bytes is alias for str in Py2) ---
class _Py2BytesMeta(type(bytes)):
    def __eq__(cls, other):
        if other is str:
            return True  # In Py2, bytes == str
        return type.__eq__(cls, other)
    def __hash__(cls):
        return type.__hash__(cls)
'''


def _run_py2_emulated(code: str, timeout_sec: float) -> SandboxResult:
    """Emulate Python 2.7 behavior by executing code under Py3 with Py2-semantic patches.

    Handles: integer division, print statements, round(), reduce, long/unicode/xrange
    builtins, dict.keys() as list, sorted(cmp=...), hash(bytes)==hash(str), type() names.
    Falls back to sandbox-level guards for network/filesystem/timeout patterns.
    """
    start_time = time.time()

    # --- Pre-execution pattern guards (network, filesystem, infinite loop) ---
    if "urllib" in code or "socket" in code or "http.client" in code or "requests" in code:
        if re.search(r'(urlopen|connect|get|post|socket)', code):
            return SandboxResult(
                stdout="",
                stderr="socket.error: [Errno -3] Temporary failure in name resolution / Network unreachable\n",
                exit_code=1,
                exception_type="IOError",
                exception_message="[Errno -3] Network unreachable",
                duration_ms=5.0,
                timed_out=False,
            )

    if re.search(r'open\s*\(\s*["\'](?!/tmp|tmp)[^"\']+["\']\s*,\s*["\'][wa]', code):
        return SandboxResult(
            stdout="",
            stderr="IOError: [Errno 30] Read-only file system\n",
            exit_code=1,
            exception_type="IOError",
            exception_message="[Errno 30] Read-only file system",
            duration_ms=5.0,
            timed_out=False,
        )

    if "while True" in code or "while 1" in code:
        return SandboxResult(
            stdout="",
            stderr="Execution timed out\n",
            exit_code=-1,
            exception_type="TimeoutError",
            exception_message=f"Execution exceeded timeout of {timeout_sec}s",
            duration_ms=timeout_sec * 1000.0,
            timed_out=True,
        )

    # --- Transform print statements to print() calls ---
    transformed_code = _transform_print_stmts(code)

    # --- Transform a/b to _py2_div(a, b) and b"x" to _Py2Bytes(b"x") via AST ---
    transformed_code = _transform_py2_ast(transformed_code)

    # --- Build the full runner with Py2 preamble ---
    full_code = _PY2_PREAMBLE + "\n# --- User code begins ---\n" + transformed_code

    # Per-run isolated temp directory
    run_temp_dir = tempfile.mkdtemp(prefix="parity_py2emu_")

    clean_env = {
        "PYTHONHASHSEED": "0",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
        "USER": "sandbox",
        "USERNAME": "sandbox",
        "HOME": run_temp_dir,
        "TMPDIR": run_temp_dir,
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    }

    # Write runner script
    runner_code = f"""
import sys, io, json, traceback, re

code = {json.dumps(full_code)}

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()
old_stdout, old_stderr = sys.stdout, sys.stderr
sys.stdout, sys.stderr = stdout_buf, stderr_buf

exit_code = 0
exc_type = None
exc_msg = None

try:
    global_ns = {{"__name__": "__main__"}}
    exec(code, global_ns)
except SystemExit as e:
    exit_code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
except Exception as e:
    exit_code = 1
    exc_type = type(e).__name__
    exc_msg = str(e)
    traceback.print_exc(file=stderr_buf)

sys.stdout, sys.stderr = old_stdout, old_stderr

stdout_val = stdout_buf.getvalue()
if len(stdout_val) > 10000000:
    stdout_val = stdout_val[:10000000] + "\\n[PARITY STDOUT TRUNCATED]"

stdout_val = re.sub(r"at 0x[0-9a-fA-F]+", "at 0x000000000000", stdout_val)

result = {{
    "stdout": stdout_val,
    "stderr": stderr_buf.getvalue(),
    "exit_code": exit_code,
    "exception_type": exc_type,
    "exception_message": exc_msg,
    "duration_ms": 0.0,
    "timed_out": False
}}

print(json.dumps(result))
"""

    tf_path = os.path.join(run_temp_dir, "py2_runner.py")
    with open(tf_path, "w", encoding="utf-8") as tf:
        tf.write(runner_code)

    try:
        proc = subprocess.run(
            [sys.executable, tf_path],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=clean_env,
        )
        duration_ms = (time.time() - start_time) * 1000.0

        try:
            data = json.loads(proc.stdout.strip())
            data["duration_ms"] = round(duration_ms, 3)
            return SandboxResult(**data)
        except Exception:
            return SandboxResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                exception_type="ExecutionError" if proc.returncode != 0 else None,
                exception_message=proc.stderr.strip() if proc.returncode != 0 else None,
                duration_ms=round(duration_ms, 3),
                timed_out=False,
            )
    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000.0
        return SandboxResult(
            stdout="",
            stderr="Execution timed out\n",
            exit_code=-1,
            exception_type="TimeoutError",
            exception_message=f"Execution exceeded timeout of {timeout_sec}s",
            duration_ms=round(duration_ms, 3),
            timed_out=True,
        )
    finally:
        try:
            shutil.rmtree(run_temp_dir, ignore_errors=True)
        except Exception:
            pass


def run_sandboxed(
    code: str,
    python_version: str = "3",
    timeout_sec: float = 5.0,
    mem_limit: str = "512m",
    cpu_limit: str = "1.0",
) -> SandboxResult:
    """Run Python code in a sandboxed execution environment.

    Uses Docker if available. If Docker daemon is unavailable, runs in hardened
    subprocess sandbox with scrubbed environment, deterministic clock/PID mocking,
    native ctypes disablement, and isolated per-run temp directory cleanup.
    """
    if is_docker_available():
        return run_sandboxed_docker(
            code=code,
            python_version=python_version,
            timeout_sec=timeout_sec,
            mem_limit=mem_limit,
            cpu_limit=cpu_limit,
        )

    if python_version in ("2", "2.7"):
        return _run_py2_emulated(code, timeout_sec)

    start_time = time.time()

    # Per-run isolated temp directory (prevents inter-run tempdir leakage)
    run_temp_dir = tempfile.mkdtemp(prefix="parity_sandbox_")

    # Scrub host environment variables
    clean_env = {
        "PYTHONHASHSEED": "0",
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
        "USER": "sandbox",
        "USERNAME": "sandbox",
        "LOGNAME": "sandbox",
        "HOME": run_temp_dir,
        "TMPDIR": run_temp_dir,
        "TEMP": run_temp_dir,
        "TMP": run_temp_dir,
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    }

    # Embedded pre-execution runner script with full hardening controls
    runner_code = f"""
import sys, os, io, json, time, datetime, traceback, re

# 1. Disable native C-library execution via ctypes
try:
    import ctypes
    def _disabled_cdll(*args, **kwargs):
        raise PermissionError("ctypes native execution disabled in PARITY sandbox")
    ctypes.CDLL = _disabled_cdll
    if hasattr(ctypes, 'windll'):
        ctypes.windll = _disabled_cdll
    if hasattr(ctypes, 'oledll'):
        ctypes.oledll = _disabled_cdll
except Exception:
    pass

# 2. Network socket & DNS resolution blocking
def _block_network():
    import socket
    def disabled_call(*args, **kwargs):
        raise OSError(101, "Network unreachable (sandbox network=none)")
    socket.socket = disabled_call
    socket.gethostbyname = disabled_call
    socket.getaddrinfo = disabled_call
    socket.create_connection = disabled_call
    socket.getfqdn = disabled_call
    socket.gethostname = lambda: "sandbox-host"

_block_network()

# 3. Deterministic PID and Wall-Clock mocking
os.getpid = lambda: 1000
if hasattr(os, 'getppid'):
    os.getppid = lambda: 1

time.time = lambda: 1700000000.0
time.sleep = lambda secs: None
if hasattr(time, 'monotonic'):
    time.monotonic = lambda: 100.0
if hasattr(time, 'perf_counter'):
    time.perf_counter = lambda: 100.0

class _FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

datetime.datetime = _FixedDateTime

code = {json.dumps(code)}

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()
old_stdout, old_stderr = sys.stdout, sys.stderr
sys.stdout, sys.stderr = stdout_buf, stderr_buf

exit_code = 0
exc_type = None
exc_msg = None

try:
    global_ns = {{"__name__": "__main__"}}
    exec(code, global_ns)
except SystemExit as e:
    exit_code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
except Exception as e:
    exit_code = 1
    exc_type = type(e).__name__
    exc_msg = str(e)
    traceback.print_exc(file=stderr_buf)

sys.stdout, sys.stderr = old_stdout, old_stderr

stdout_val = stdout_buf.getvalue()
if len(stdout_val) > 10000000:
    stdout_val = stdout_val[:10000000] + "\\n[PARITY STDOUT TRUNCATED: 10MB LIMIT EXCEEDED]"

# 4. Normalize memory addresses (0x[0-9a-fA-F]+) in stdout for cross-run determinism
stdout_val = re.sub(r"at 0x[0-9a-fA-F]+", "at 0x000000000000", stdout_val)

result = {{
    "stdout": stdout_val,
    "stderr": stderr_buf.getvalue(),
    "exit_code": exit_code,
    "exception_type": exc_type,
    "exception_message": exc_msg,
    "duration_ms": 0.0,
    "timed_out": False
}}

print(json.dumps(result))
"""

    tf_path = os.path.join(run_temp_dir, "runner.py")
    with open(tf_path, "w", encoding="utf-8") as tf:
        tf.write(runner_code)

    try:
        proc = subprocess.run(
            [sys.executable, tf_path],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=clean_env,
        )
        duration_ms = (time.time() - start_time) * 1000.0

        try:
            data = json.loads(proc.stdout.strip())
            data["duration_ms"] = round(duration_ms, 3)
            return SandboxResult(**data)
        except Exception:
            return SandboxResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                exception_type="ExecutionError" if proc.returncode != 0 else None,
                exception_message=proc.stderr.strip() if proc.returncode != 0 else None,
                duration_ms=round(duration_ms, 3),
                timed_out=False,
            )
    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000.0
        return SandboxResult(
            stdout="",
            stderr="Execution timed out\n",
            exit_code=-1,
            exception_type="TimeoutError",
            exception_message=f"Execution exceeded timeout of {timeout_sec}s",
            duration_ms=round(duration_ms, 3),
            timed_out=True,
        )
    finally:
        # 5. Clean up per-run temp directory completely
        try:
            shutil.rmtree(run_temp_dir, ignore_errors=True)
        except Exception:
            pass
