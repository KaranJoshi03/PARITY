# Ledger 003
Phase / session: Phase 0 Scaffold Audit
Model: Gemini 3.6 Flash
What I asked: Audit snapshot tool for secret leakage paths.
What the AI said/produced: Snapshot should_exclude only checked filename patterns like *.key and *.secret, omitting secret directories and extensionless key names.
Why it was wrong (category: false-pass): Files inside secrets/ or .ssh/ (e.g. secrets/db.json, id_rsa) were included in ZIP archives.
How I caught it (my own reasoning / a test / the Skeptic / a real run): Security audit of file path matching rules.
How it was fixed: Added secret directory matching, extensionless key patterns, and case-insensitive normalization.
Transcript link: N/A (local execution log)
Would my prompt have prevented it? (yes/no, how): Yes, by specifying directory-level secret exclusion requirements explicitly.
