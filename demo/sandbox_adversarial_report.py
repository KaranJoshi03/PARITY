"""Adversarial sandbox evaluation report generator.

Runs all 7 security attack vectors against the sandbox and prints detailed output.
"""

import os
import sys
import json
import time
from parity.sandbox import run_sandboxed


def run_adversarial_report():
    print("=" * 75)
    print("PARITY ADVERSARIAL SANDBOX SECURITY REPORT")
    print("=" * 75)

    # 1. Fork bomb
    print("\n--- 1. FORK BOMB ATTEMPT ---")
    code1 = """
import os, sys
if hasattr(os, 'fork'):
    try:
        for i in range(100):
            os.fork()
    except Exception as e:
        print("FORK_FAILED: " + str(e))
else:
    print("NO_FORK_ON_OS")
"""
    res1 = run_sandboxed(code1, python_version="3", timeout_sec=2.0)
    print(f"Stdout:      {res1.stdout.strip()}")
    print(f"Stderr:      {res1.stderr.strip()}")
    print(f"Exit Code:   {res1.exit_code}")
    print(f"Timed out:   {res1.timed_out}")

    # 2. Huge memory allocation
    print("\n--- 2. HUGE MEMORY ALLOCATION ---")
    code2 = "a = 'X' * (10**9)"
    res2 = run_sandboxed(code2, python_version="3", timeout_sec=2.0)
    print(f"Stdout:      {res2.stdout.strip()}")
    print(f"Stderr:      {res2.stderr.strip()[:100]}")
    print(f"Exit Code:   {res2.exit_code}")
    print(f"Exception:   {res2.exception_type} - {res2.exception_message}")

    # 3. Huge stdout flood
    print("\n--- 3. HUGE STDOUT FLOOD ---")
    code3 = "import sys; sys.stdout.write('A' * (10**7))"
    res3 = run_sandboxed(code3, python_version="3", timeout_sec=3.0)
    print(f"Stdout Len:  {len(res3.stdout)} bytes")
    print(f"Exit Code:   {res3.exit_code}")
    print(f"Duration:    {res3.duration_ms} ms")

    # 4. Reading /etc/passwd
    print("\n--- 4. READING /etc/passwd ---")
    code4 = """
try:
    with open('/etc/passwd') as f:
        data = f.read()
    print("READ_SUCCESS: " + data[:40].replace('\\n', ' '))
except Exception as e:
    print("READ_FAILED: " + type(e).__name__ + ": " + str(e))
"""
    res4 = run_sandboxed(code4, python_version="3")
    print(f"Stdout:      {res4.stdout.strip()}")
    print(f"Exit Code:   {res4.exit_code}")

    # 5. DNS lookup
    print("\n--- 5. DNS LOOKUP / NETWORK ACCESS ---")
    code5 = "import socket; socket.gethostbyname('google.com')"
    res5 = run_sandboxed(code5, python_version="3")
    print(f"Stdout:      {res5.stdout.strip()}")
    print(f"Stderr:      {res5.stderr.strip()}")
    print(f"Exit Code:   {res5.exit_code}")
    print(f"Exception:   {res5.exception_type} - {res5.exception_message}")

    # 6. Writing to project directory
    print("\n--- 6. WRITING TO PROJECT DIRECTORY ---")
    code6 = "with open('forbidden_test_file.txt', 'w') as f: f.write('hacked')"
    res6 = run_sandboxed(code6, python_version="2")
    print(f"Stdout:      {res6.stdout.strip()}")
    print(f"Stderr:      {res6.stderr.strip()}")
    print(f"Exit Code:   {res6.exit_code}")
    print(f"Exception:   {res6.exception_type} - {res6.exception_message}")
    print(f"File Exists: {os.path.exists('forbidden_test_file.txt')}")

    # 7. Leaving zombie processes
    print("\n--- 7. LEAVING ZOMBIE PROCESSES ---")
    code7 = """
import subprocess, sys
p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
print("SPAWNED_PID_" + str(p.pid))
"""
    res7 = run_sandboxed(code7, python_version="3", timeout_sec=1.5)
    print(f"Stdout:      {res7.stdout.strip()}")
    print(f"Exit Code:   {res7.exit_code}")
    print(f"Timed Out:   {res7.timed_out}")

    print("\n" + "=" * 75)
    print("ADVERSARIAL SECURITY SUITE COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    run_adversarial_report()
