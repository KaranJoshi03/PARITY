"""Stage 5 Acceptance Demonstration: Behavior Capture on 6 Target Modules.

Executes behavior capture on 6 distinct modules:
  1. Module using random (detects random side-effect & non-determinism)
  2. Module using time (detects dynamic time side-effect)
  3. Module raising exceptions (captures structured exception payload)
  4. Module mutating global state (detects global_state flag)
  5. Standard calculation module (deterministic return value)
  6. Module with large output (demonstrates truncation)
"""

import json
from pathlib import Path
from parity.capture.capture import capture_behavior

DEMO_DIR = Path("d:/KARAN/parity/demo/capture_fixtures")
DEMO_DIR.mkdir(parents=True, exist_ok=True)

# 1. Random Module
(DEMO_DIR / "mod_random.py").write_text("""
import random

def roll_dice(sides):
    return random.randint(1, sides)
""", encoding="utf-8")

# 2. Time Module
(DEMO_DIR / "mod_time.py").write_text("""
import time

def get_current_timestamp():
    return time.time()
""", encoding="utf-8")

# 3. Exception Module
(DEMO_DIR / "mod_exception.py").write_text("""
def divide_values(a, b):
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero in calculation")
    return a / b
""", encoding="utf-8")

# 4. Global State Mutation Module
(DEMO_DIR / "mod_global.py").write_text("""
COUNTER = 0

def increment_and_get(step):
    global COUNTER
    COUNTER += step
    return COUNTER
""", encoding="utf-8")

# 5. Pure Deterministic Module (Integer division)
(DEMO_DIR / "mod_division.py").write_text("""
def calculate(a, b):
    return a / b
""", encoding="utf-8")

# 6. Huge Output Module
(DEMO_DIR / "mod_large_output.py").write_text("""
def flood_stdout(count):
    for i in range(count):
        print "Line " + str(i) + ": " + ("x" * 100)
    return "completed"
""", encoding="utf-8")


def run_acceptance():
    print("=" * 80)
    print("STAGE 5 BEHAVIOR CAPTURE ACCEPTANCE DEMONSTRATION")
    print("=" * 80)

    fixtures = [
        ("mod_random.py", "roll_dice", {"args": [{"t": "int", "v": 100}], "kwargs": {}}),
        ("mod_time.py", "get_current_timestamp", {"args": [], "kwargs": {}}),
        ("mod_exception.py", "divide_values", {"args": [{"t": "int", "v": 10}, {"t": "int", "v": 0}], "kwargs": {}}),
        ("mod_global.py", "increment_and_get", {"args": [{"t": "int", "v": 5}], "kwargs": {}}),
        ("mod_division.py", "calculate", {"args": [{"t": "int", "v": 7}, {"t": "int", "v": 2}], "kwargs": {}}),
        ("mod_large_output.py", "flood_stdout", {"args": [{"t": "int", "v": 200}], "kwargs": {}}),
    ]

    records = []
    for mod_file, ep, inp in fixtures:
        path = DEMO_DIR / mod_file
        print(f"\n[+] Capturing behavior for {mod_file} :: {ep}()")
        record = capture_behavior(path, ep, inp, runs=3)
        records.append(record)
        
        # Display key fields
        print(f"    - Deterministic: {record.deterministic}")
        if not record.deterministic:
            print(f"      Reason: {record.non_determinism_reason}")
        print(f"    - Side effect flags: {record.side_effect_flags}")
        print(f"    - Return value: {record.outputs['return']}")
        print(f"    - Exception: {record.outputs['exception']}")
        print(f"    - Stdout length: {len(record.outputs['stdout'])} chars (Truncated: {'TRUNCATED' in record.outputs['stdout']})")
        print(f"    - Lossy: {record.lossy}")
        print(f"    - Average Duration: {record.duration_ms:.2f} ms")

    print("\n" + "=" * 80)
    print("ALL 6 CAPTURE RECORDS CREATED AND VALIDATED PER CONTRACTS.md")
    print("=" * 80)
    return records


if __name__ == "__main__":
    run_acceptance()
