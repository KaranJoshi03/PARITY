# Ledger 001
Phase / session: Phase 0 Scaffold Build
Model: Gemini 3.6 Flash
What I asked: Build scaffold under src/, tests/, eval/, demo/.
What the AI said/produced: Created pyproject.toml with build-backend = "setuptools.backends._legacy:_Backend".
Why it was wrong (category: hallucinated-API): Non-existent setuptools build backend string caused pip install -e . to crash.
How I caught it (my own reasoning / a test / the Skeptic / a real run): A real run (pip install -e .).
How it was fixed: Replaced with valid setuptools.build_meta backend.
Transcript link: N/A (local execution log)
Would my prompt have prevented it? (yes/no, how): Yes, by enforcing explicit build configuration syntax validation.
