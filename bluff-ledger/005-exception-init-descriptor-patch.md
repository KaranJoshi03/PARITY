# Ledger 005
Phase / session: Phase 0 Fixtures & Sandbox Emulation
Model: Gemini 3.8 Flash (Low)
What I asked: Add Python 2 exception .message attribute support in the emulation preamble.
What the AI said/produced: Attempted to monkey-patch `Exception.__init__` and built-in exception classes (`ValueError`, `TypeError`) by rebinding `_cls.__init__` directly on built-in types.
Why it was wrong (category: hallucinated-API): Built-in core C-extension types and descriptors in CPython are immutable at runtime; attempting to reassign `Exception.__init__` or call unbound `Exception.__init__.__get__(Exception)` raises `TypeError: descriptor '__init__' for 'Exception' objects doesn't apply to a 'type' object` during runner initialization.
Taxonomy Classification:
- ID: DIV-PREAMBLE-001
- Root Cause Category: UNREPRESENTED (CPython C-Extension Runtime Immutability)
- Sub-Category: SEM-EXC-MODEL (Exception Constructor Protocol)
- Symptom Type: Unhandled TypeError
- Trigger Condition: On Py2 runner initialization
- Contract Impact: CONTRACTS.md §Comparator Rules: R5 (Exception class and message)
How I caught it (my own reasoning / a test / the Skeptic / a real run): A real run (`python -c "from parity.sandbox import run_sandboxed; run_sandboxed('print(1+1)', '2')"`).
How it was fixed: Removed the invalid builtin descriptor mutation and implemented Python 2 exception message support via AST attribute rewriting (`visit_Attribute` translating `e.message` to `getattr(e, 'message', str(e))`) and builtins `hasattr` interception.
Transcript link: N/A (local execution log)
Would my prompt have prevented it? (yes/no, how): No, runtime execution against the Python interpreter is necessary to verify builtin type immutability constraints.
