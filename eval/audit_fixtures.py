"""Audit script for meta-test requirements across all 20 fixtures."""

from pathlib import Path
from parity.sandbox import run_sandboxed

FIXTURES_DIR = Path("d:/KARAN/parity/fixtures")

def audit():
    rows = []
    for p in sorted(FIXTURES_DIR.iterdir()):
        if not p.is_dir():
            continue
        f_py2 = p / "original_py2.py"
        f_cpy3 = p / "correct_py3.py"
        f_wpy3 = p / "subtly_wrong_py3.py"
        if not (f_py2.exists() and f_cpy3.exists() and f_wpy3.exists()):
            continue

        r2 = run_sandboxed(f_py2.read_text(encoding="utf-8"), python_version="2")
        r3c = run_sandboxed(f_cpy3.read_text(encoding="utf-8"), python_version="3")
        r3w = run_sandboxed(f_wpy3.read_text(encoding="utf-8"), python_version="3")

        out2 = r2.stdout.strip() if r2.exit_code == 0 else f"ERROR:{r2.exception_type}"
        out3c = r3c.stdout.strip() if r3c.exit_code == 0 else f"ERROR:{r3c.exception_type}"
        out3w = r3w.stdout.strip() if r3w.exit_code == 0 else f"ERROR:{r3w.exception_type}"

        c1 = (r2.exit_code == 0)
        c2 = (out2 == out3c and r2.exit_code == r3c.exit_code)
        c3 = (out2 != out3w or r2.exit_code != r3w.exit_code)

        rows.append({
            "dir": p.name,
            "c1_py2_runs": c1,
            "c2_correct_matches": c2,
            "c3_wrong_differs": c3,
            "out2": out2,
            "out3c": out3c,
            "out3w": out3w,
            "r2_exit": r2.exit_code,
            "r3c_exit": r3c.exit_code,
            "r3w_exit": r3w.exit_code,
        })

    print(f"Total fixtures evaluated: {len(rows)}")
    for r in rows:
        status = "PASS" if (r["c1_py2_runs"] and r["c2_correct_matches"] and r["c3_wrong_differs"]) else "FAIL"
        print(f"{r['dir']:<25} | {status:<4} | C1={r['c1_py2_runs']} C2={r['c2_correct_matches']} C3={r['c3_wrong_differs']} | Py2: {r['out2']} (exit {r['r2_exit']}) | CorrectPy3: {r['out3c']} (exit {r['r3c_exit']}) | WrongPy3: {r['out3w']} (exit {r['r3w_exit']})")

if __name__ == "__main__":
    audit()
