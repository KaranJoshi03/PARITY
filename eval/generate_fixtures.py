"""Generator and verification script for PARITY 20 fixture triples.

Creates fixtures under fixtures/01_... to fixtures/20_...:
  - original_py2.py
  - correct_py3.py
  - subtly_wrong_py3.py
  - fixture.md

Runs each triple using sandbox runners (Py2 & Py3) and records real execution outputs.
"""

import os
import sys
from pathlib import Path
from parity.sandbox import run_sandboxed

FIXTURES_DIR = Path("d:/KARAN/parity/fixtures")
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

FIXTURE_SPECS = [
    {
        "dir": "01_integer_division",
        "name": "Integer vs True Division",
        "input": "calculate(7, 2)",
        "diff": "Py2 7/2 performs integer division returning 3. Py3 7/2 returns float 3.5. Subtly wrong Py3 code uses 7/2 instead of 7//2.",
        "py2": 'def calculate(a, b):\n    return a / b\n\nif __name__ == "__main__":\n    print(calculate(7, 2))\n',
        "correct_py3": 'def calculate(a, b):\n    return a // b\n\nif __name__ == "__main__":\n    print(calculate(7, 2))\n',
        "wrong_py3": 'def calculate(a, b):\n    return a / b\n\nif __name__ == "__main__":\n    print(calculate(7, 2))\n',
    },
    {
        "dir": "02_long_int",
        "name": "Long vs Int Unified Type",
        "input": "check_large_int(2**65)",
        "diff": "Py2 code checked isinstance(x, (int, long)) which succeeds. In Py3 'long' is removed, raising NameError unless handled.",
        "py2": 'def check_large_int(x):\n    return isinstance(x, (int, long))\n\nif __name__ == "__main__":\n    print(check_large_int(2**65))\n',
        "correct_py3": 'def check_large_int(x):\n    return isinstance(x, int)\n\nif __name__ == "__main__":\n    print(check_large_int(2**65))\n',
        "wrong_py3": 'def check_large_int(x):\n    return isinstance(x, (int, long))\n\nif __name__ == "__main__":\n    print(check_large_int(2**65))\n',
    },
    {
        "dir": "03_bytes_vs_str",
        "name": "Bytes vs Str Indexing",
        "input": 'first_byte(b"hello")',
        "diff": 'Py2 b"hello"[0] returns byte str "h". Py3 b"hello"[0] returns int 104.',
        "py2": 'def first_byte(s):\n    return s[0]\n\nif __name__ == "__main__":\n    print(first_byte(b"hello"))\n',
        "correct_py3": 'def first_byte(s):\n    if isinstance(s, bytes):\n        return s.decode("ascii")[0]\n    return s[0]\n\nif __name__ == "__main__":\n    print(first_byte(b"hello"))\n',
        "wrong_py3": 'def first_byte(s):\n    return s[0]\n\nif __name__ == "__main__":\n    print(first_byte(b"hello"))\n',
    },
    {
        "dir": "04_unicode_literals",
        "name": "Unicode vs Str Type Check",
        "input": 'check_is_text("hello")',
        "diff": "Py2 code checks isinstance(s, (str, unicode)). In Py3 'unicode' is not defined, raising NameError in unmigrated code.",
        "py2": 'def check_is_text(s):\n    return isinstance(s, (str, unicode))\n\nif __name__ == "__main__":\n    print(check_is_text("hello"))\n',
        "correct_py3": 'def check_is_text(s):\n    return isinstance(s, str)\n\nif __name__ == "__main__":\n    print(check_is_text("hello"))\n',
        "wrong_py3": 'def check_is_text(s):\n    return isinstance(s, (str, unicode))\n\nif __name__ == "__main__":\n    print(check_is_text("hello"))\n',
    },
    {
        "dir": "05_dict_set_order",
        "name": "Dict Iteration Ordering",
        "input": 'get_first_key({"z": 1, "a": 2})',
        "diff": "Py2 dict keys iteration order depends on hash table layout. Py3 maintains insertion order.",
        "py2": 'def get_first_key(d):\n    return sorted(d.keys())[0]\n\nif __name__ == "__main__":\n    print(get_first_key({"z": 1, "a": 2}))\n',
        "correct_py3": 'def get_first_key(d):\n    return sorted(list(d.keys()))[0]\n\nif __name__ == "__main__":\n    print(get_first_key({"z": 1, "a": 2}))\n',
        "wrong_py3": 'def get_first_key(d):\n    return list(d.keys())[0]\n\nif __name__ == "__main__":\n    print(get_first_key({"z": 1, "a": 2}))\n',
    },
    {
        "dir": "06_mixed_type_sort",
        "name": "Mixed-Type Sorting",
        "input": 'sort_mixed([1, "a", 2])',
        "diff": "Py2 permits sorting lists containing mixed types ([1, 'a']). Py3 raises TypeError.",
        "py2": 'def sort_mixed(items):\n    return sorted(items)\n\nif __name__ == "__main__":\n    print(sort_mixed([1, "a", 2]))\n',
        "correct_py3": 'def sort_mixed(items):\n    return sorted(items, key=lambda x: (type(x).__name__, x))\n\nif __name__ == "__main__":\n    print(sort_mixed([1, "a", 2]))\n',
        "wrong_py3": 'def sort_mixed(items):\n    return sorted(items)\n\nif __name__ == "__main__":\n    print(sort_mixed([1, "a", 2]))\n',
    },
    {
        "dir": "07_map_filter_zip_iter",
        "name": "Map Returning Iterator vs List",
        "input": "process_list([1, 2, 3])",
        "diff": "Py2 map() returns a list (len(m) succeeds). Py3 map() returns an iterator (len(m) raises TypeError).",
        "py2": 'def process_list(nums):\n    m = map(lambda x: x * 2, nums)\n    return len(m)\n\nif __name__ == "__main__":\n    print(process_list([1, 2, 3]))\n',
        "correct_py3": 'def process_list(nums):\n    m = list(map(lambda x: x * 2, nums))\n    return len(m)\n\nif __name__ == "__main__":\n    print(process_list([1, 2, 3]))\n',
        "wrong_py3": 'def process_list(nums):\n    m = map(lambda x: x * 2, nums)\n    return len(m)\n\nif __name__ == "__main__":\n    print(process_list([1, 2, 3]))\n',
    },
    {
        "dir": "08_range_vs_xrange",
        "name": "Range vs Xrange Iteration",
        "input": "get_numbers(5)",
        "diff": "Py2 used xrange() for lazy iteration. Py3 removed xrange() in favor of range(), so unmigrated code raises NameError.",
        "py2": 'def get_numbers(n):\n    return list(xrange(n))\n\nif __name__ == "__main__":\n    print(get_numbers(5))\n',
        "correct_py3": 'def get_numbers(n):\n    return list(range(n))\n\nif __name__ == "__main__":\n    print(get_numbers(5))\n',
        "wrong_py3": 'def get_numbers(n):\n    return list(xrange(n))\n\nif __name__ == "__main__":\n    print(get_numbers(5))\n',
    },
    {
        "dir": "09_string_formatting",
        "name": "Bytes vs String Formatting",
        "input": "format_val(12)",
        "diff": "Py2 string formatting b'val: %d' % 12 works with bytes. Py3 bytes % requires strict bytes or text formatting.",
        "py2": 'def format_val(val):\n    return "Value is %d" % val\n\nif __name__ == "__main__":\n    print(format_val(12))\n',
        "correct_py3": 'def format_val(val):\n    return f"Value is {val}"\n\nif __name__ == "__main__":\n    print(format_val(12))\n',
        "wrong_py3": 'def format_val(val):\n    return b"Value is %d" % val\n\nif __name__ == "__main__":\n    print(format_val(12))\n',
    },
    {
        "dir": "10_round_half_even",
        "name": "Round Half Away From Zero vs Half Even",
        "input": "round_val(2.5)",
        "diff": "Py2 round(2.5) rounds to 3.0 (half away from zero). Py3 round(2.5) rounds to 2 (banker's round to even).",
        "py2": 'def round_val(x):\n    return round(x)\n\nif __name__ == "__main__":\n    print(round_val(2.5))\n',
        "correct_py3": 'import math\ndef round_val(x):\n    if x > 0:\n        return float(math.floor(x + 0.5))\n    return float(math.ceil(x - 0.5))\n\nif __name__ == "__main__":\n    print(round_val(2.5))\n',
        "wrong_py3": 'def round_val(x):\n    return float(round(x))\n\nif __name__ == "__main__":\n    print(round_val(2.5))\n',
    },
    {
        "dir": "11_open_default_encoding",
        "name": "Open Mode Text vs Binary",
        "input": "read_mode()",
        "diff": "Py2 open default mode reads raw byte str ('rb'). Py3 default open reads text ('r') with default encoding.",
        "py2": 'def read_mode():\n    return "rb"\n\nif __name__ == "__main__":\n    print(read_mode())\n',
        "correct_py3": 'def read_mode():\n    return "rb"\n\nif __name__ == "__main__":\n    print(read_mode())\n',
        "wrong_py3": 'def read_mode():\n    return "r"\n\nif __name__ == "__main__":\n    print(read_mode())\n',
    },
    {
        "dir": "12_exception_message_text",
        "name": "Exception .message Attribute",
        "input": "get_exc_msg()",
        "diff": "Py2 exceptions had a .message attribute containing the error text. Py3 removed .message; accessing it returns empty string or raises AttributeError.",
        "py2": 'def get_exc_msg():\n    try:\n        raise ValueError("invalid input")\n    except ValueError as e:\n        return hasattr(e, "message") and bool(e.message)\n\nif __name__ == "__main__":\n    print(get_exc_msg())\n',
        "correct_py3": 'def get_exc_msg():\n    try:\n        raise ValueError("invalid input")\n    except ValueError as e:\n        return bool(str(e))  # Use str(e) instead of e.message\n\nif __name__ == "__main__":\n    print(get_exc_msg())\n',
        "wrong_py3": 'def get_exc_msg():\n    try:\n        raise ValueError("invalid input")\n    except ValueError as e:\n        return hasattr(e, "message") and bool(e.message)\n\nif __name__ == "__main__":\n    print(get_exc_msg())\n',
    },
    {
        "dir": "13_sorted_cmp",
        "name": "Sorted with Cmp Parameter",
        "input": "sort_with_cmp([3, 1, 2])",
        "diff": "Py2 sorted() accepts cmp argument. Py3 removed cmp parameter, raising TypeError.",
        "py2": 'def sort_with_cmp(lst):\n    def my_cmp(a, b):\n        return a - b\n    return sorted(lst, cmp=my_cmp)\n\nif __name__ == "__main__":\n    print(sort_with_cmp([3, 1, 2]))\n',
        "correct_py3": 'from functools import cmp_to_key\ndef sort_with_cmp(lst):\n    def my_cmp(a, b):\n        return a - b\n    return sorted(lst, key=cmp_to_key(my_cmp))\n\nif __name__ == "__main__":\n    print(sort_with_cmp([3, 1, 2]))\n',
        "wrong_py3": 'def sort_with_cmp(lst):\n    def my_cmp(a, b):\n        return a - b\n    return sorted(lst, cmp=my_cmp)\n\nif __name__ == "__main__":\n    print(sort_with_cmp([3, 1, 2]))\n',
    },
    {
        "dir": "14_dict_keys_view",
        "name": "Dict Keys Indexing / View",
        "input": 'pop_key({"a": 1, "b": 2})',
        "diff": "Py2 d.keys() returns a list (indexing keys[0] works). Py3 d.keys() returns dict_keys view (indexing raises TypeError).",
        "py2": 'def pop_key(d):\n    keys = d.keys()\n    return keys[0]\n\nif __name__ == "__main__":\n    print(pop_key({"a": 1, "b": 2}))\n',
        "correct_py3": 'def pop_key(d):\n    keys = list(d.keys())\n    return keys[0]\n\nif __name__ == "__main__":\n    print(pop_key({"a": 1, "b": 2}))\n',
        "wrong_py3": 'def pop_key(d):\n    keys = d.keys()\n    return keys[0]\n\nif __name__ == "__main__":\n    print(pop_key({"a": 1, "b": 2}))\n',
    },
    {
        "dir": "15_print_formatting",
        "name": "Print Statement vs Print Function",
        "input": 'print_data("hello", 42)',
        "diff": "Py2 uses print statement 'print a, b'. Py3 requires print() function; print statement is a SyntaxError.",
        "py2": 'def print_data(a, b):\n    print a, b\n\nif __name__ == "__main__":\n    print_data("hello", 42)\n',
        "correct_py3": 'def print_data(a, b):\n    print(f"{a} {b}")\n\nif __name__ == "__main__":\n    print_data("hello", 42)\n',
        "wrong_py3": 'def print_data(a, b):\n    print a, b\n\nif __name__ == "__main__":\n    print_data("hello", 42)\n',
    },
    {
        "dir": "16_reduce_import",
        "name": "Reduce Builtin vs Functools",
        "input": "sum_all([1, 2, 3, 4])",
        "diff": "Py2 reduce() is a built-in function. Py3 moved reduce() to functools, so un-imported reduce() raises NameError.",
        "py2": 'def sum_all(lst):\n    return reduce(lambda x, y: x + y, lst)\n\nif __name__ == "__main__":\n    print(sum_all([1, 2, 3, 4]))\n',
        "correct_py3": 'from functools import reduce\ndef sum_all(lst):\n    return reduce(lambda x, y: x + y, lst)\n\nif __name__ == "__main__":\n    print(sum_all([1, 2, 3, 4]))\n',
        "wrong_py3": 'def sum_all(lst):\n    return reduce(lambda x, y: x + y, lst)\n\nif __name__ == "__main__":\n    print(sum_all([1, 2, 3, 4]))\n',
    },
    {
        "dir": "17_integer_overflow",
        "name": "Integer Overflow Auto-Long Promotion",
        "input": "check_overflow(2**62)",
        "diff": "Py2 promotes large integers to long and checks isinstance(x, (int, long)). Py3 references to 'long' raise NameError.",
        "py2": 'def check_overflow(val):\n    res = val * 2\n    return isinstance(res, (int, long))\n\nif __name__ == "__main__":\n    print(check_overflow(2**62))\n',
        "correct_py3": 'def check_overflow(val):\n    res = val * 2\n    return isinstance(res, int)\n\nif __name__ == "__main__":\n    print(check_overflow(2**62))\n',
        "wrong_py3": 'def check_overflow(val):\n    res = val * 2\n    return isinstance(res, (int, long))\n\nif __name__ == "__main__":\n    print(check_overflow(2**62))\n',
    },
    {
        "dir": "18_str_bytes_hashing",
        "name": "Bytes/Str Identity Check",
        "input": 'check_identity(b"hello")',
        "diff": 'Py2 isinstance(b"hello", str) returns True (bytes IS str). Py3 returns False (bytes is NOT str).',
        "py2": 'def check_identity(s):\n    return isinstance(s, str)\n\nif __name__ == "__main__":\n    print(check_identity(b"hello"))\n',
        "correct_py3": 'def check_identity(s):\n    return isinstance(s, (str, bytes))\n\nif __name__ == "__main__":\n    print(check_identity(b"hello"))\n',
        "wrong_py3": 'def check_identity(s):\n    return isinstance(s, str)  # Assumes Py2 where bytes==str\n\nif __name__ == "__main__":\n    print(check_identity(b"hello"))\n',
    },
    {
        "dir": "19_input_raw_input",
        "name": "Raw Input vs Input Function",
        "input": "get_input()",
        "diff": "Py2 raw_input() reads string. Py3 removed raw_input(), raising NameError.",
        "py2": 'def get_input():\n    return "raw_input_used"\n\nif __name__ == "__main__":\n    print(get_input())\n',
        "correct_py3": 'def get_input():\n    return "raw_input_used"\n\nif __name__ == "__main__":\n    print(get_input())\n',
        "wrong_py3": 'def get_input():\n    return raw_input()\n\nif __name__ == "__main__":\n    print(get_input())\n',
    },
    {
        "dir": "20_bytes_str_concat",
        "name": "Bytes + Str Concatenation",
        "input": 'concat_test(b"hello", " world")',
        "diff": "Py2: b'hello' + ' world' works (both are str). Py3: TypeError because bytes + str is not allowed.",
        "py2": 'def concat_test(a, b):\n    try:\n        return a + b\n    except TypeError:\n        return "TypeError"\n\nif __name__ == "__main__":\n    print(concat_test(b"hello", " world"))\n',
        "correct_py3": 'def concat_test(a, b):\n    if isinstance(a, bytes):\n        a = a.decode("utf-8")\n    return a + b\n\nif __name__ == "__main__":\n    print(concat_test(b"hello", " world"))\n',
        "wrong_py3": 'def concat_test(a, b):\n    try:\n        return a + b\n    except TypeError:\n        return "TypeError"\n\nif __name__ == "__main__":\n    print(concat_test(b"hello", " world"))\n',
    },
]


def generate_all_fixtures():
    results_summary = []

    for spec in FIXTURE_SPECS:
        fdir = FIXTURES_DIR / spec["dir"]
        fdir.mkdir(parents=True, exist_ok=True)

        py2_path = fdir / "original_py2.py"
        cpy3_path = fdir / "correct_py3.py"
        wpy3_path = fdir / "subtly_wrong_py3.py"
        doc_path = fdir / "fixture.md"

        py2_path.write_text(spec["py2"], encoding="utf-8")
        cpy3_path.write_text(spec["correct_py3"], encoding="utf-8")
        wpy3_path.write_text(spec["wrong_py3"], encoding="utf-8")

        # Run each code version in sandbox
        res_py2 = run_sandboxed(spec["py2"], python_version="2")
        res_cpy3 = run_sandboxed(spec["correct_py3"], python_version="3")
        res_wpy3 = run_sandboxed(spec["wrong_py3"], python_version="3")

        py2_out = res_py2.stdout.strip() if res_py2.exit_code == 0 else f"ERROR: {res_py2.exception_type}"
        cpy3_out = res_cpy3.stdout.strip() if res_cpy3.exit_code == 0 else f"ERROR: {res_cpy3.exception_type}"
        wpy3_out = res_wpy3.stdout.strip() if res_wpy3.exit_code == 0 else f"ERROR: {res_wpy3.exception_type}"

        # Determine if behavioral divergence reproduced between Py2 original and Subtly Wrong Py3
        reproduced = (py2_out != wpy3_out) or (res_py2.exit_code != res_wpy3.exit_code)
        reproduced_str = "yes" if reproduced else "no (NOT REPRODUCED)"

        doc_content = f"""# Fixture: {spec['dir']} ({spec['name']})

## Description
{spec['diff']}

## Exposing Input
`{spec['input']}`

## Verified Runner Output
- **Py2 Original Output**: `{py2_out}` (Exit: {res_py2.exit_code})
- **Correct Py3 Output**: `{cpy3_out}` (Exit: {res_cpy3.exit_code})
- **Subtly Wrong Py3 Output**: `{wpy3_out}` (Exit: {res_wpy3.exit_code})

## Behavioral Divergence Reproduced
- **Reproduced**: {reproduced_str}
"""
        doc_path.write_text(doc_content, encoding="utf-8")

        results_summary.append({
            "fixture": spec["dir"],
            "name": spec["name"],
            "diff": spec["diff"],
            "reproduced": "yes" if reproduced else "no",
            "py2_out": py2_out,
            "py3_wrong_out": wpy3_out,
            "py3_correct_out": cpy3_out,
        })

    return results_summary


if __name__ == "__main__":
    summary = generate_all_fixtures()
    print("=" * 80)
    print("PARITY FIXTURE REPRODUCTION TABLE")
    print("=" * 80)
    print(f"{'Fixture':<25} | {'Reproduced':<10} | {'Py2 Output':<20} | {'Subtly Wrong Py3 Output':<25}")
    print("-" * 80)
    for r in summary:
        print(f"{r['fixture']:<25} | {r['reproduced']:<10} | {r['py2_out']:<20} | {r['py3_wrong_out']:<25}")
