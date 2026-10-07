"""Runnable probes for the 6 sandbox attack/leakage/non-reproducibility vectors.

Probes:
  1. Inter-run temp directory persistence (/tmp shared across runs in fallback mode)
  2. Host environment variable leakage (os.getenv('USER') / host OS state)
  3. Native C-library socket bypass via ctypes / low-level C calls
  4. Non-deterministic wall-clock timestamps (time.time() / datetime.now())
  5. Heap memory address non-determinism (id() / repr() memory addresses)
  6. OS Process ID non-determinism (os.getpid() process table variation)
"""

import os
import sys
import tempfile
import time
from parity.sandbox import run_sandboxed


def run_limitation_probes():
    print("=" * 75)
    print("SANDBOX LIMITATION & ESCAPE PROBES")
    print("=" * 75)

    # Probe 1: Inter-run temp directory persistence (isolated per-run tempdir check)
    print("\n--- Probe 1: Inter-Run Temp Directory Persistence ---")
    code1_write = "import os, tempfile; open(os.path.join(tempfile.gettempdir(), 'parity_probe1.tmp'), 'w').write('secret')"
    code1_read = "import os, tempfile; print('EXISTS' if os.path.exists(os.path.join(tempfile.gettempdir(), 'parity_probe1.tmp')) else 'CLEAN')"

    res1_a = run_sandboxed(code1_write, python_version="3")
    res1_b = run_sandboxed(code1_read, python_version="3")
    print(f"Run A (write to tempdir) exit: {res1_a.exit_code}")
    print(f"Run B (read tempdir file):   {res1_b.stdout.strip()}")




    # Probe 2: Host environment variable leakage
    print("\n--- Probe 2: Host Environment Variable Leakage ---")
    code2 = "import os; print('USER=' + str(os.getenv('USER') or os.getenv('USERNAME')))"
    res2 = run_sandboxed(code2, python_version="3")
    print(f"Host Environment Leaked:     {res2.stdout.strip()}")

    # Probe 3: Native C-library socket bypass via ctypes
    print("\n--- Probe 3: C-Library Socket Bypass via ctypes ---")
    code3 = """
import os, sys, ctypes
try:
    if hasattr(ctypes, 'CDLL'):
        libc = ctypes.CDLL(None) if os.name == 'posix' else ctypes.windll.kernel32
        print("CTYPES_LOADED: " + str(libc is not None))
    else:
        print("CTYPES_UNAVAILABLE")
except Exception as e:
    print("CTYPES_ERROR: " + type(e).__name__ + ": " + str(e))
"""
    res3 = run_sandboxed(code3, python_version="3")
    print(f"ctypes Bypass Output:        {res3.stdout.strip()}")

    # Probe 4: Non-deterministic wall-clock timestamps
    print("\n--- Probe 4: Non-Deterministic Wall-Clock Timestamps ---")
    code4 = "import time; print(time.time())"
    res4_a = run_sandboxed(code4, python_version="3")
    time.sleep(0.1)
    res4_b = run_sandboxed(code4, python_version="3")
    print(f"Run A timestamp:             {res4_a.stdout.strip()}")
    print(f"Run B timestamp:             {res4_b.stdout.strip()}")
    print(f"Timestamps Equal?            {res4_a.stdout.strip() == res4_b.stdout.strip()}")

    # Probe 5: Heap memory address non-determinism
    print("\n--- Probe 5: Heap Memory Address Non-Determinism ---")
    code5 = "obj = object(); print(repr(obj))"
    res5_a = run_sandboxed(code5, python_version="3")
    res5_b = run_sandboxed(code5, python_version="3")
    print(f"Run A object repr:           {res5_a.stdout.strip()}")
    print(f"Run B object repr:           {res5_b.stdout.strip()}")
    print(f"Reprs Equal?                 {res5_a.stdout.strip() == res5_b.stdout.strip()}")

    # Probe 6: OS Process ID non-determinism
    print("\n--- Probe 6: OS Process ID Non-Determinism ---")
    code6 = "import os; print(os.getpid())"
    res6_a = run_sandboxed(code6, python_version="3")
    res6_b = run_sandboxed(code6, python_version="3")
    print(f"Run A PID:                   {res6_a.stdout.strip()}")
    print(f"Run B PID:                   {res6_b.stdout.strip()}")
    print(f"PIDs Equal?                  {res6_a.stdout.strip() == res6_b.stdout.strip()}")

    print("\n" + "=" * 75)
    print("ALL 6 PROBES EXECUTED SUCCESSFULLY")
    print("=" * 75)


if __name__ == "__main__":
    run_limitation_probes()
