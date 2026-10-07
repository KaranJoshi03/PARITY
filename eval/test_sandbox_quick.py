"""Quick test of run_sandboxed for Py2 and Py3 with fixture code."""
from parity.sandbox import run_sandboxed, is_docker_available

print(f"Docker available: {is_docker_available()}")

# Test 1: Integer division in Py2
code_div = 'def calculate(a, b):\n    return a / b\n\nif __name__ == "__main__":\n    print(calculate(7, 2))\n'
r2 = run_sandboxed(code_div, python_version="2")
print(f"Py2 div: stdout={r2.stdout!r} exit={r2.exit_code}")

# Test 2: Integer division in Py3  
r3 = run_sandboxed(code_div, python_version="3")
print(f"Py3 div: stdout={r3.stdout!r} exit={r3.exit_code}")

# Test 3: Bytes indexing
code_bytes = 'def first_byte(s):\n    return s[0]\n\nif __name__ == "__main__":\n    print(first_byte(b"hello"))\n'
r2b = run_sandboxed(code_bytes, python_version="2")
print(f"Py2 bytes: stdout={r2b.stdout!r} exit={r2b.exit_code}")
r3b = run_sandboxed(code_bytes, python_version="3")
print(f"Py3 bytes: stdout={r3b.stdout!r} exit={r3b.exit_code}")

# Test 4: Print statement  
code_print = 'def print_data(a, b):\n    print a, b\n\nif __name__ == "__main__":\n    print_data("hello", 42)\n'
r2p = run_sandboxed(code_print, python_version="2")
print(f"Py2 print stmt: stdout={r2p.stdout!r} exit={r2p.exit_code}")
r3p = run_sandboxed(code_print, python_version="3")
print(f"Py3 print stmt: stdout={r3p.stdout!r} exit={r3p.exit_code}")

# Test 5: round(2.5)
code_round = 'print(round(2.5))\n'
r2r = run_sandboxed(code_round, python_version="2")
print(f"Py2 round: stdout={r2r.stdout!r} exit={r2r.exit_code}")
r3r = run_sandboxed(code_round, python_version="3")
print(f"Py3 round: stdout={r3r.stdout!r} exit={r3r.exit_code}")
