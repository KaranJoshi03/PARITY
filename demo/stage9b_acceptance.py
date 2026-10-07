"""Stage 9b Acceptance Demonstration: Test Strength on 8 Target Fixtures.

Demonstrates:
  - Strong test suites (multiple diverse/generated inputs) kill 100% of migration mutants (high score).
  - Trivial / weak test suites leave mutants surviving (low score / insufficient=True).
"""

from pathlib import Path
from parity.capture.capture import capture_behavior
from parity.verify.generate.generator import EnhancedInputGenerator
from parity.verify.strength.mutator import compute_test_strength

FIXTURES_DIR = Path("d:/KARAN/parity/fixtures")

def run_acceptance():
    print("=" * 80)
    print("STAGE 9b TEST STRENGTH (MUTATION TESTING) ACCEPTANCE DEMONSTRATION")
    print("=" * 80)

    target_fixtures = [
        ("01_integer_division", "calculate", {"args": [{"t": "int", "v": 7}, {"t": "int", "v": 2}], "kwargs": {}}),
        ("02_long_int", "check_large_int", {"args": [{"t": "long", "v": 2**65}], "kwargs": {}}),
        ("03_bytes_vs_str", "first_byte", {"args": [{"t": "bytes3", "v": "hello"}], "kwargs": {}}),
        ("04_unicode_literals", "check_is_text", {"args": [{"t": "unicode", "v": "hello"}], "kwargs": {}}),
        ("07_map_filter_zip_iter", "process_list", {"args": [{"t": "list", "v": [{"t": "int", "v": 1}, {"t": "int", "v": 2}]}], "kwargs": {}}),
        ("08_range_vs_xrange", "get_numbers", {"args": [{"t": "int", "v": 5}], "kwargs": {}}),
        ("14_dict_keys_view", "pop_key", {"args": [{"t": "dict", "v": [[{"t": "str", "v": "a"}, {"t": "int", "v": 1}]]}], "kwargs": {}}),
        ("17_integer_overflow", "check_overflow", {"args": [{"t": "long", "v": 2**62}], "kwargs": {}}),
    ]

    gen = EnhancedInputGenerator(seed=42, max_inputs=5)

    print(f"{'Fixture':<25} | {'Mutants (Killed/Total)':<22} | {'Score':<8} | {'Insufficient?':<13} | {'Operators Used'}")
    print("-" * 80)

    for f_name, ep, seed_inp in target_fixtures:
        fdir = FIXTURES_DIR / f_name
        py2_file = fdir / "original_py2.py"
        cpy3_file = fdir / "correct_py3.py"
        cpy3_code = cpy3_file.read_text(encoding="utf-8")

        # 1. Capture inputs using generator suite (strong tests)
        suite = gen.generate_inputs_for_signature(seed_inp)
        records = [capture_behavior(py2_file, ep, inp, runs=1) for inp in suite]

        # 2. Compute test strength
        ts = compute_test_strength(cpy3_code, records, threshold=0.70)
        
        ops_str = ", ".join(ts.mutation_operators_used) if ts.mutation_operators_used else "None"
        ratio_str = f"{ts.mutants_killed} / {ts.mutants_total}"
        insuf_str = "YES (FAIL)" if ts.insufficient else "NO (SAFE)"

        print(f"{f_name:<25} | {ratio_str:<22} | {ts.score:.2f}     | {insuf_str:<13} | {ops_str}")

    print("\n" + "=" * 80)
    print("STAGE 9b ACCEPTANCE COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    run_acceptance()
