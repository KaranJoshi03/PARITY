# Decision 001: Pipeline architecture selection

Date: 2026-10-04

Context:
PARITY needs an architecture for its seven stages (capture, migrate, diffcheck, test-strength, verdict, eval harness, demo). Three options were evaluated: A (Pipeline-of-Files), B (In-Process Library with SQLite), C (Event-Sourced with Append-Only Log). Concrete failure scenarios were analyzed for each. Architecture A was then hardened into "Enhanced A+" to eliminate its known failure modes while preserving its core simplicity.

Options considered (with trade-offs):
- A (Pipeline-of-Files): Simplest, highest inspectability, fastest to build (6–8 sessions). Weakness: no provenance tracking, stale files can silently accumulate, no isolation of migrated code, no traceability between artifacts.
- B (SQLite Library): Structured cross-module queries, single source of truth. Weakness: migrated code runs in-process (structural, not fixable without changing the architecture), binary DB hard to inspect, non-reproducible results due to process-state pollution across modules. Legacy code is full of import-time side effects, making this the worst-case architecture for PARITY's target domain.
- C (Event-Sourced Log): Full audit trail, immutable history, high per-module inspectability. Weakness: over-engineered for 30–60 modules, reducer logic is subtle and a false-SAFE bug surface, version skew between events produced by different tool versions is hard to detect and invalidate without destroying the audit trail.
- A+ (Enhanced Pipeline-of-Files): A with immutable per-run directories, manifest with hashes, artifact envelopes with provenance, pre-stage validation, subprocess isolation for migrated code, deterministic verdict. Adds ~40% build effort over A but eliminates all three known failure scenarios.

Decision:
Enhanced A+ (hardened Pipeline-of-Files).

Why:
1. B's in-process poisoning is structural and unfixable without becoming A or C. Legacy Python 2 code (our exact target) is full of import-time side effects. This eliminates B.
2. C's reducer complexity and version-skew problem are real, and the event-sourcing machinery is not justified for a linear pipeline over 30–60 modules. The audit trail benefit can be approximated by A+'s immutable run directories (each run is a snapshot). This deprioritizes C.
3. A's failure modes (stale files, no provenance, no isolation) are all addressable without changing the architecture. The Enhanced A+ design adds: immutable run IDs, per-run directories, manifest with hashes, artifact envelopes with run_id/version/parent hashes, pre-stage validation, subprocess isolation. These are additive hardening, not a new architecture.
4. A+ preserves A's core strengths: every intermediate artifact is a human-readable JSON file, stages are independent CLI scripts, the verdict is a pure function, and the whole thing is inspectable with `cat`, `jq`, and `diff`.

What I rejected and why:
- B: Structural false-SAFE path from in-process execution of untrusted migrated code. Cannot be fixed without subprocess isolation, which turns B into A.
- C: Reducer complexity is a new false-SAFE bug surface that doesn't exist in A. Event-sourcing's strength (immutability) becomes a weakness when tool versions are found buggy after events are recorded. Invalidation requires either a new event type (added complexity) or deleting the log (destroying the audit trail). Not justified for this scale.
- Plain A: Known failure modes (stale files, no provenance, no isolation) are unacceptable given PARITY's fail-closed contract.

What could make this wrong:
- If the project scales to hundreds of modules with frequent re-runs, the "new run ID per re-run" model becomes expensive (many redundant captures). C's incremental approach would then be cheaper.
- If cross-module querying becomes critical (e.g., "which comparator rule correlated with false verdicts"), the lack of a database will be painful. A future phase could add an optional SQLite index built from run artifacts without changing the pipeline.
- If AI agents struggle to implement the validation logic correctly, the validation itself becomes a false-confidence source. The test matrix (T1–T15) is designed to catch this, but the tests themselves must be correct.

Evidence / transcript link:
- Architecture options: see artifact `architecture_options.md`
- Failure scenarios: see artifact `failure_scenarios.md`
- Enhanced A+ specification: see artifact `enhanced_a_plus_spec.md`
