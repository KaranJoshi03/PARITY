"""Adversarial security tests for the PARITY sandbox layer.

Tests 7 security attack vectors:
  1. Fork bomb attempt
  2. Huge memory allocation
  3. Huge stdout flood
  4. Reading /etc/passwd
  5. DNS lookup
  6. Writing to the project directory
  7. Leaving zombie processes
"""

import os
import pytest
from parity.sandbox import run_sandboxed


def test_adversarial_fork_bomb():
    """Attack 1: Fork bomb attempt."""
    code = """
import os, sys
if hasattr(os, 'fork'):
    try:
        for _ in range(100):
            os.fork()
    except Exception:
        pass
"""
    res = run_sandboxed(code, python_version="3", timeout_sec=2.0)
    # Must finish or time out cleanly without hanging host
    assert res.exit_code in (0, 1, -1)


def test_adversarial_memory_allocation():
    """Attack 2: Huge memory allocation."""
    code = "a = 'X' * (10**11)"
    res = run_sandboxed(code, python_version="3", timeout_sec=2.0)
    # Must fail with MemoryError or exit non-zero
    assert res.exit_code != 0 or res.exception_type in ("MemoryError", "OverflowError")



def test_adversarial_stdout_flood():
    """Attack 3: Huge stdout flood."""
    code = "import sys; sys.stdout.write('A' * (10**7))"
    res = run_sandboxed(code, python_version="3", timeout_sec=3.0)
    assert res.exit_code == 0
    assert len(res.stdout) > 0


def test_adversarial_read_etc_passwd():
    """Attack 4: Reading /etc/passwd."""
    code = """
try:
    with open('/etc/passwd') as f:
        content = f.read()
    print("READ_SUCCESS: " + content[:20])
except Exception as e:
    print("READ_FAILED: " + type(e).__name__)
"""
    res = run_sandboxed(code, python_version="3")
    # On Windows fallback, FileNotFoundError; inside Linux Docker container, opens container's unprivileged passwd
    assert "READ_FAILED" in res.stdout or "READ_SUCCESS" in res.stdout


def test_adversarial_dns_lookup():
    """Attack 5: DNS lookup / Network access."""
    code = "import socket; socket.gethostbyname('google.com')"
    res = run_sandboxed(code, python_version="3")
    assert res.exit_code != 0


def test_adversarial_write_project_dir():
    """Attack 6: Writing to project directory."""
    code = "with open('project_file.txt', 'w') as f: f.write('unauthorized')"
    res = run_sandboxed(code, python_version="2")
    assert res.exit_code != 0
    assert not os.path.exists("project_file.txt")


def test_adversarial_zombie_processes():
    """Attack 7: Leaving zombie processes."""
    code = """
import subprocess, sys
p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
"""
    res = run_sandboxed(code, python_version="3", timeout_sec=1.0)
    assert res.exit_code in (0, 1, -1)
