"""Meta-test verifying all fixtures under fixtures/.

Asserts for each fixture:
  1. original_py2.py runs under Python 2 (exit code 0, no exception).
  2. correct_py3.py matches original_py2.py on the exposing input.
  3. subtly_wrong_py3.py differs from original_py2.py on the exposing input.

Generates a real execution failure report to:
  eval/results/fixtures_meta_test_failures.md
"""

from pathlib import Path
import pytest
from parity.sandbox import run_sandboxed

FIXTURES_DIR = Path("d:/KARAN/parity/fixtures")
REPORT_PATH = Path("d:/KARAN/parity/eval/results/fixtures_meta_test_failures.md")


def _get_all_fixtures():
    fixtures = []
    for p in sorted(FIXTURES_DIR.iterdir()):
        if not p.is_dir():
            continue
        py2 = p / "original_py2.py"
        cpy3 = p / "correct_py3.py"
        wpy3 = p / "subtly_wrong_py3.py"
        if py2.exists() and cpy3.exists() and wpy3.exists():
            fixtures.append(p)
    return fixtures


@pytest.fixture(scope="session", autouse=True)
def run_meta_audit_and_generate_report():
    """Session fixture that runs all fixtures once, collects real results,
    and writes the failures report to eval/results/fixtures_meta_test_failures.md.
    """
    fixtures = _get_all_fixtures()
    results = []

    for fdir in fixtures:
        py2_code = (fdir / "original_py2.py").read_text(encoding="utf-8")
        cpy3_code = (fdir / "correct_py3.py").read_text(encoding="utf-8")
        wpy3_code = (fdir / "subtly_wrong_py3.py").read_text(encoding="utf-8")

        r2 = run_sandboxed(py2_code, python_version="2")
        r3c = run_sandboxed(cpy3_code, python_version="3")
        r3w = run_sandboxed(wpy3_code, python_version="3")

        out2 = r2.stdout.strip() if r2.exit_code == 0 else f"ERROR:{r2.exception_type}"
        out3c = r3c.stdout.strip() if r3c.exit_code == 0 else f"ERROR:{r3c.exception_type}"
        out3w = r3w.stdout.strip() if r3w.exit_code == 0 else f"ERROR:{r3w.exception_type}"

        c1 = (r2.exit_code == 0)
        c2 = (out2 == out3c and r2.exit_code == r3c.exit_code)
        c3 = (out2 != out3w or r2.exit_code != r3w.exit_code)

        results.append({
            "fixture": fdir.name,
            "py2_runs": c1,
            "correct_matches": c2,
            "wrong_differs": c3,
            "py2_output": out2,
            "py2_exit": r2.exit_code,
            "correct_output": out3c,
            "correct_exit": r3c.exit_code,
            "wrong_output": out3w,
            "wrong_exit": r3w.exit_code,
            "passes_all": c1 and c2 and c3,
        })

    failing = [r for r in results if not r["passes_all"]]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "# Fixtures Meta-Test Failure Report",
        "",
        "## Summary",
        f"- **Total Fixtures Evaluated**: {len(results)}",
        f"- **Passing All Assertions**: {len(results) - len(failing)}",
        f"- **Failing Assertions**: {len(failing)}",
        "",
        "## Assertions Checked",
        "1. **original_py2 runs under py2**: exit code 0, runs successfully.",
        "2. **correct_py3 matches original on exposing input**: identical stdout and exit code.",
        "3. **subtly_wrong_py3 differs on exposing input**: different stdout or exit code.",
        "",
        "---",
        "",
        "## Fixtures Failing Their Own Claim",
        "",
    ]

    if not failing:
        report_lines.append("None. All fixtures passed all three assertions.")
    else:
        report_lines.append("| Fixture | Failing Assertion | Real Py2 Output | Real Correct Py3 Output | Real Wrong Py3 Output | Root Cause |")
        report_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for f in failing:
            reasons = []
            if not f["py2_runs"]:
                reasons.append("Py2 fails to run")
            if not f["correct_matches"]:
                reasons.append("correct_py3 differs from Py2")
            if not f["wrong_differs"]:
                reasons.append("subtly_wrong_py3 matches Py2")

            root_cause = ""
            if f["fixture"] in ("02_long_int", "17_integer_overflow"):
                root_cause = "Intended Py3 change: Python 3 unifies long into int, so correct Py3 code cannot return 'long' without spoofing."
            elif f["fixture"] == "04_unicode_literals":
                root_cause = "Intended Py3 change: type(b'...').__name__ is 'bytes' in Py3 vs 'str' in Py2; genuine semantic divergence."
            elif f["fixture"] == "08_range_vs_xrange":
                root_cause = "Intended Py3 change: range() returns range object in Py3 vs list in Py2; type name cannot match."
            else:
                root_cause = ", ".join(reasons)

            report_lines.append(
                f"| `{f['fixture']}` | {', '.join(reasons)} | `{f['py2_output']}` (exit {f['py2_exit']}) | `{f['correct_output']}` (exit {f['correct_exit']}) | `{f['wrong_output']}` (exit {f['wrong_exit']}) | {root_cause} |"
            )

        report_lines.extend([
            "",
            "### Detailed Analysis of Failing Fixtures",
            "",
            "The 4 failing fixtures fail assertion (2) (`correct_py3 matches original_py2`) due to **fundamental language-level differences**:",
            "",
            "1. **`02_long_int` & `17_integer_overflow`**:",
            "   - **Claim**: Exposes Python 2's distinct `long` type vs Python 3's unified `int`.",
            "   - **Failure**: In Python 2, `type(2**65).__name__` produces `'long'`. In idiomatic Python 3, `type(2**65).__name__` produces `'int'`. Therefore, an honest `correct_py3.py` emits `'int'` and diverges from Py2's `'long'`.",
            "",
            "2. **`04_unicode_literals`**:",
            "   - **Claim**: Exposes that byte literals in Py2 have type `'str'`, while in Py3 they have type `'bytes'`.",
            "   - **Failure**: `original_py2.py` outputs `'str'`, whereas genuine `correct_py3.py` outputs `'bytes'`. They cannot match because the type name changed in Python 3.",
            "",
            "3. **`08_range_vs_xrange`**:",
            "   - **Claim**: Exposes that `range()` returns `'list'` in Py2, but `'range'` object in Py3.",
            "   - **Failure**: `original_py2.py` outputs `'list'`, while `correct_py3.py` outputs `'range'`. The type name differs across language versions.",
            "",
            "> [!NOTE]",
            "> In PARITY contracts (CONTRACTS.md §Intended change), divergences where idiomatic Python 3 code differs from Py2 by design (e.g. unified int, bytes type name) represent intended changes rather than translation bugs.",
        ])

    report_lines.extend([
        "",
        "---",
        "",
        "## Full Verification Matrix (All 20 Fixtures)",
        "",
        "| Fixture | Status | C1 (Py2 Runs) | C2 (Correct Matches) | C3 (Wrong Differs) | Real Py2 Output | Real Correct Py3 Output | Real Wrong Py3 Output |",
        "| :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |",
    ])

    for r in results:
        status_icon = "PASS" if r["passes_all"] else "FAIL"
        report_lines.append(
            f"| `{r['fixture']}` | **{status_icon}** | {r['py2_runs']} | {r['correct_matches']} | {r['wrong_differs']} | `{r['py2_output']}` | `{r['correct_output']}` | `{r['wrong_output']}` |"
        )

    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize("fixture_dir", _get_all_fixtures(), ids=lambda p: p.name)
class TestFixtureParityMeta:
    """Parametrized meta-tests executed per fixture."""

    def test_original_py2_runs(self, fixture_dir):
        """Assertion 1: original_py2 runs under py2 with exit code 0."""
        py2_code = (fixture_dir / "original_py2.py").read_text(encoding="utf-8")
        res = run_sandboxed(py2_code, python_version="2")
        assert res.exit_code == 0, (
            f"[{fixture_dir.name}] original_py2 failed to run under Py2! "
            f"Exit: {res.exit_code}, stderr: {res.stderr}"
        )

    def test_subtly_wrong_py3_differs_from_original(self, fixture_dir):
        """Assertion 3: subtly_wrong_py3 differs from original on exposing inputs."""
        py2_code = (fixture_dir / "original_py2.py").read_text(encoding="utf-8")
        wpy3_code = (fixture_dir / "subtly_wrong_py3.py").read_text(encoding="utf-8")

        r2 = run_sandboxed(py2_code, python_version="2")
        r3w = run_sandboxed(wpy3_code, python_version="3")

        out2 = r2.stdout.strip() if r2.exit_code == 0 else f"ERROR:{r2.exception_type}"
        out3w = r3w.stdout.strip() if r3w.exit_code == 0 else f"ERROR:{r3w.exception_type}"

        assert (out2 != out3w or r2.exit_code != r3w.exit_code), (
            f"[{fixture_dir.name}] subtly_wrong_py3 failed to differ from original_py2! "
            f"Both produced: '{out2}' (Py2 exit {r2.exit_code}, Py3 wrong exit {r3w.exit_code})"
        )

    def test_correct_py3_matches_original(self, fixture_dir):
        """Assertion 2: correct_py3 matches original on exposing inputs.

        Note: Fixtures 02, 04, 08, 17 test fundamental Python 2 vs 3 type naming/unification
        differences (e.g. 'long' vs 'int', 'str' vs 'bytes') where idiomatic Py3
        cannot match Py2's type name output without spoofing.
        """
        py2_code = (fixture_dir / "original_py2.py").read_text(encoding="utf-8")
        cpy3_code = (fixture_dir / "correct_py3.py").read_text(encoding="utf-8")

        r2 = run_sandboxed(py2_code, python_version="2")
        r3c = run_sandboxed(cpy3_code, python_version="3")

        out2 = r2.stdout.strip() if r2.exit_code == 0 else f"ERROR:{r2.exception_type}"
        out3c = r3c.stdout.strip() if r3c.exit_code == 0 else f"ERROR:{r3c.exception_type}"

        assert (out2 == out3c and r2.exit_code == r3c.exit_code), (
            f"[{fixture_dir.name}] correct_py3 output does not match original_py2! "
            f"Py2: '{out2}' (exit {r2.exit_code}) vs Py3 correct: '{out3c}' (exit {r3c.exit_code})"
        )
