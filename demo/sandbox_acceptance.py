"""Sandbox acceptance test script.

Demonstrates all 5 acceptance criteria:
  (a) print(3/2) prints 1 under py2 and 1.5 under py3
  (b) an infinite loop is killed by the timeout
  (c) network access fails
  (d) writing outside tmp fails
  (e) a py2-only syntax (print statement) runs in py2 runner and fails in py3
"""

import json
from parity.sandbox import run_sandboxed


def run_acceptance_suite():
    print("=" * 70)
    print("PARITY SANDBOX ACCEPTANCE SUITE EXECUTING...")
    print("=" * 70)

    # (a) Integer division behavior
    code_div = "print(3/2)"
    res_py2_div = run_sandboxed(code_div, python_version="2")
    res_py3_div = run_sandboxed(code_div, python_version="3")

    print("\n--- (a) Integer Division print(3/2) ---")
    print(f"Py2 Output: {res_py2_div.stdout.strip()} (Exit: {res_py2_div.exit_code})")
    print(f"Py3 Output: {res_py3_div.stdout.strip()} (Exit: {res_py3_div.exit_code})")
    assert res_py2_div.stdout.strip() == "1", f"Expected '1', got '{res_py2_div.stdout.strip()}'"
    assert res_py3_div.stdout.strip() == "1.5", f"Expected '1.5', got '{res_py3_div.stdout.strip()}'"

    # (b) Infinite loop killed by timeout
    code_loop = "while True: pass"
    res_loop = run_sandboxed(code_loop, python_version="3", timeout_sec=1.0)
    print("\n--- (b) Infinite Loop Timeout ---")
    print(f"Timed out: {res_loop.timed_out}")
    print(f"Exception: {res_loop.exception_type} - {res_loop.exception_message}")
    print(f"Duration:  {res_loop.duration_ms} ms")
    assert res_loop.timed_out is True, "Expected timed_out=True"

    # (c) Network access fails
    code_net = "import socket; s = socket.socket(); s.connect(('8.8.8.8', 53))"
    res_net = run_sandboxed(code_net, python_version="3")
    print("\n--- (c) Network Access Restriction ---")
    print(f"Exit Code: {res_net.exit_code}")
    print(f"Exception: {res_net.exception_type} - {res_net.exception_message}")
    assert res_net.exit_code != 0, "Expected non-zero exit code on network call"

    # (d) Writing outside /tmp fails
    code_write = "with open('forbidden_write.txt', 'w') as f: f.write('secret')"
    res_write = run_sandboxed(code_write, python_version="2")
    print("\n--- (d) Read-Only File System (Writing Outside /tmp) ---")
    print(f"Exit Code: {res_write.exit_code}")
    print(f"Exception: {res_write.exception_type} - {res_write.exception_message}")
    assert res_write.exit_code != 0, "Expected write failure outside /tmp"

    # (e) Py2-only print statement syntax
    code_syntax = 'print "hello py2"'
    res_py2_syntax = run_sandboxed(code_syntax, python_version="2")
    res_py3_syntax = run_sandboxed(code_syntax, python_version="3")

    print("\n--- (e) Py2 Syntax vs Py3 Syntax Error ---")
    print(f"Py2 Syntax Output:    {res_py2_syntax.stdout.strip()} (Exit: {res_py2_syntax.exit_code})")
    print(f"Py3 Syntax Exception: {res_py3_syntax.exception_type} - {res_py3_syntax.exception_message}")
    assert res_py2_syntax.exit_code == 0, "Expected Py2 print statement to succeed under Py2"
    assert res_py3_syntax.exit_code != 0, "Expected Py2 print statement to fail under Py3"
    assert res_py3_syntax.exception_type == "SyntaxError", "Expected SyntaxError under Py3"

    print("\n" + "=" * 70)
    print("ALL 5 ACCEPTANCE CRITERIA PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_acceptance_suite()
