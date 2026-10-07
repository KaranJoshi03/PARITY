"""Stage 7 Acceptance Demonstration: Run Differential Verifier over All 20 Fixtures.

For each fixture:
  1. Captures Python 2 behavior on the exposing input.
  2. Runs correct_py3.py and verifies parity is achieved (no divergences).
  3. Runs subtly_wrong_py3.py and verifies divergence is detected (showing category and rule applied).
"""

from pathlib import Path
from parity.capture.capture import capture_behavior
from parity.verify.verifier import verify_differential

FIXTURES_DIR = Path("d:/KARAN/parity/fixtures")

# Exposing input arguments per fixture
FIXTURE_INPUTS = {
    "01_integer_division": ("calculate", {"args": [{"t": "int", "v": 7}, {"t": "int", "v": 2}], "kwargs": {}}),
    "02_long_int": ("check_large_int", {"args": [{"t": "long", "v": 2**65}], "kwargs": {}}),
    "03_bytes_vs_str": ("first_byte", {"args": [{"t": "bytes3", "v": "hello"}], "kwargs": {}}),
    "04_unicode_literals": ("check_is_text", {"args": [{"t": "unicode", "v": "hello"}], "kwargs": {}}),
    "05_dict_set_order": ("get_first_key", {"args": [{"t": "dict", "v": [[{"t": "str", "v": "z"}, {"t": "int", "v": 1}], [{"t": "str", "v": "a"}, {"t": "int", "v": 2}]]}], "kwargs": {}}),
    "06_mixed_type_sort": ("sort_mixed", {"args": [{"t": "list", "v": [{"t": "int", "v": 1}, {"t": "str", "v": "a"}, {"t": "int", "v": 2}]}], "kwargs": {}}),
    "07_map_filter_zip_iter": ("process_list", {"args": [{"t": "list", "v": [{"t": "int", "v": 1}, {"t": "int", "v": 2}, {"t": "int", "v": 3}]}], "kwargs": {}}),
    "08_range_vs_xrange": ("get_numbers", {"args": [{"t": "int", "v": 5}], "kwargs": {}}),
    "09_string_formatting": ("format_val", {"args": [{"t": "int", "v": 12}], "kwargs": {}}),
    "10_round_half_even": ("round_val", {"args": [{"t": "float", "v": 2.5}], "kwargs": {}}),
    "11_open_default_encoding": ("read_mode", {"args": [], "kwargs": {}}),
    "12_exception_message_text": ("get_exc_msg", {"args": [], "kwargs": {}}),
    "13_sorted_cmp": ("sort_with_cmp", {"args": [{"t": "list", "v": [{"t": "int", "v": 3}, {"t": "int", "v": 1}, {"t": "int", "v": 2}]}], "kwargs": {}}),
    "14_dict_keys_view": ("pop_key", {"args": [{"t": "dict", "v": [[{"t": "str", "v": "a"}, {"t": "int", "v": 1}], [{"t": "str", "v": "b"}, {"t": "int", "v": 2}]]}], "kwargs": {}}),
    "15_print_formatting": ("print_data", {"args": [{"t": "str", "v": "hello"}, {"t": "int", "v": 42}], "kwargs": {}}),
    "16_reduce_import": ("sum_all", {"args": [{"t": "list", "v": [{"t": "int", "v": 1}, {"t": "int", "v": 2}, {"t": "int", "v": 3}, {"t": "int", "v": 4}]}], "kwargs": {}}),
    "17_integer_overflow": ("check_overflow", {"args": [{"t": "long", "v": 2**62}], "kwargs": {}}),
    "18_str_bytes_hashing": ("check_identity", {"args": [{"t": "bytes3", "v": "hello"}], "kwargs": {}}),
    "19_input_raw_input": ("get_input", {"args": [], "kwargs": {}}),
    "20_bytes_str_concat": ("concat_test", {"args": [{"t": "bytes3", "v": "hello"}, {"t": "str", "v": " world"}], "kwargs": {}}),
}


def run_acceptance():
    print("=" * 80)
    print("STAGE 7 DIFFERENTIAL VERIFIER ACCEPTANCE DEMONSTRATION")
    print("=" * 80)
    print(f"{'Fixture':<25} | {'Correct Py3':<12} | {'Wrong Py3 Divergence':<25} | {'Rule Applied'}")
    print("-" * 80)

    for fdir in sorted(FIXTURES_DIR.iterdir()):
        if not fdir.is_dir() or fdir.name not in FIXTURE_INPUTS:
            continue
        name = fdir.name
        ep, inp = FIXTURE_INPUTS[name]
        py2_path = fdir / "original_py2.py"
        cpy3_path = fdir / "correct_py3.py"
        wpy3_path = fdir / "subtly_wrong_py3.py"

        # 1. Capture Py2
        record = capture_behavior(py2_path, ep, inp, runs=1)

        # 2. Verify Correct Py3
        cpy3_code = cpy3_path.read_text(encoding="utf-8")
        c_pass, c_divs, _ = verify_differential(record, cpy3_code)

        # 3. Verify Subtly Wrong Py3
        wpy3_code = wpy3_path.read_text(encoding="utf-8")
        w_pass, w_divs, _ = verify_differential(record, wpy3_code)

        c_status = "PARITY (OK)" if c_pass else f"FAIL ({len(c_divs)} divs)"
        if not w_pass and w_divs:
            w_desc = f"CAUGHT ({w_divs[0].category})"
            rule = w_divs[0].comparator_rule_applied
        else:
            w_desc = "MISSED (NO DIVERGENCE)"
            rule = "N/A"

        print(f"{name:<25} | {c_status:<12} | {w_desc:<25} | {rule}")

    print("=" * 80)


if __name__ == "__main__":
    run_acceptance()
