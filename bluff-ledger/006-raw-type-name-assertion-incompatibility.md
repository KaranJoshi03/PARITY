# Ledger 006
Phase / session: Phase 0 Fixtures Generation & Meta-Test Verification
Model: Gemini 3.8 Flash (Low)
What I asked: Create fixtures where correct_py3 matches original_py2 and subtly_wrong_py3 differs.
What the AI said/produced: Authored fixtures 02 (`long`), 04 (`unicode`), 08 (`range`), and 17 (`overflow`) asserting internal type names (`type(...).__name__`).
Why it was wrong (category: false-pass): Python 3 fundamentally unified `long` into `int`, separated `bytes` from `str`, and made `range` a sequence type rather than a list. An honest, idiomatic Python 3 migration returns `'int'`, `'bytes'`, and `'range'`. Expecting `correct_py3` to return `'long'` or `'str'` asserted an impossible contract where correct code would fail its own assertion unless artificially spoofed.
Taxonomy Classification:
- ID: DIV-FIXTURE-SPEC-001
- Root Cause Category: ROOT-5 (Scope & Name Resolution Semantics) / ROOT-1 (Text vs. Binary Decoupling)
- Sub-Category: SEM-TYP-UNIF (Type System Unification) & SEM-STR-MODEL (Text vs Binary Disconnection)
- Symptom Type: Semantic Assertion Incompatibility
- Trigger Condition: When comparing raw type name strings across language versions
- Contract Impact: CONTRACTS.md §Comparator Rules: R1, R2, §Intended change
How I caught it (my own reasoning / a test / the Skeptic / a real run): A real run (`python -m pytest tests/test_fixtures_meta.py`).
How it was fixed: Redesigned the four fixtures to assert observable behavioral invariants (e.g. `isinstance(x, (int, long))` in Py2 vs `isinstance(x, int)` in Py3 vs unmigrated Py3 `NameError: name 'long' is not defined`), allowing correct Py3 to match Py2 while unmigrated code diverges.
Transcript link: N/A (local execution log)
Would my prompt have prevented it? (yes/no, how): Yes, requiring all fixture assertions to test behavioral contracts rather than raw internal type name strings would have prevented this.
