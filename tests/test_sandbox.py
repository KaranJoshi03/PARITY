"""Unit tests for sandboxed execution layer."""

import pytest

from parity.sandbox import SandboxResult, run_sandboxed


def test_sandbox_python3_expression():
    res = run_sandboxed("print(3/2)", python_version="3")
    assert res.stdout.strip() == "1.5"
    assert res.exit_code == 0
    assert res.timed_out is False


def test_sandbox_python2_expression():
    res = run_sandboxed("print(3/2)", python_version="2")
    assert res.stdout.strip() == "1"
    assert res.exit_code == 0
    assert res.timed_out is False


def test_sandbox_timeout():
    res = run_sandboxed("while True: pass", python_version="3", timeout_sec=0.5)
    assert res.timed_out is True
    assert res.exit_code == -1
    assert res.exception_type == "TimeoutError"


def test_sandbox_network_blocked():
    code = "import socket; s = socket.socket(); s.connect(('8.8.8.8', 53))"
    res = run_sandboxed(code, python_version="3")
    assert res.exit_code != 0


def test_sandbox_syntax_error():
    res = run_sandboxed("print 'hello'", python_version="3")
    assert res.exit_code != 0
    assert res.exception_type == "SyntaxError"
