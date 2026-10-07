# Ledger 004
Phase / session: Phase 0 Sandbox Implementation
Model: Gemini 3.6 Flash
What I asked: Implement sandbox runner layer and run acceptance suite.
What the AI said/produced: Included f"{expr.strip('\"\'')}\n" inside sandbox.py.
Why it was wrong (category: other): Backslashes inside f-string expressions are invalid syntax in Python < 3.12.
How I caught it (my own reasoning / a test / the Skeptic / a real run): A real run (python demo/sandbox_acceptance.py).
How it was fixed: Extracted string stripping into a separate variable prior to f-string formatting.
Transcript link: N/A (local execution log)
Would my prompt have prevented it? (yes/no, how): No, syntax compatibility across Python sub-versions relies on runtime verification.
