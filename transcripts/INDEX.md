# Parity Transcript Index

## Highlights & Critical Moments

### 1. Model Hallucination & Subagent Deadlock (Phase 6 / Stage T5-T17)
- **Location**: `transcripts/phase6_testing.jsonl#L142`
- **Description**: The agent attempted parallel tool invocations on background tasks belonging to a different conversation ID, resulting in system failures and repeated execution errors.
- **Why it matters**: Demonstrates the failure mode of LLM subagents attempting cross-session task management and highlights the recovery mechanism via single-task execution.

### 2. Frozen Protocol Enforcement (Phase 4 / Corpus Builder)
- **Location**: `transcripts/phase4_corpus.jsonl#L45`
- **Description**: The user explicitly forbade altering `PREREGISTRATION.md` or changing package selection rules when initial PyPI metadata fetches failed.
- **Why it matters**: Preserves research integrity by preventing post-hoc protocol adjustments when edge cases occur in real-world datasets.

### 3. False-SAFE Comparator Gap Discovery (Phase 8 / Hostile Review)
- **Location**: `transcripts/phase8_review.jsonl#L88`
- **Description**: Hostile review revealed that `verifier.py` (R1 rule) coerced `str` vs `bytes` comparisons incorrectly under lossy serialization, falsely marking non-equivalent return types as `SAFE`.
- **Why it matters**: Identified a critical flaw in the differential verification engine prior to running the main evaluation benchmark.

### 4. Direct User Override on Architectural Scope (Phase 2 / SQLite Dual-Write)
- **Location**: `transcripts/phase2_arch.jsonl#L12`
- **Description**: User overrode the model's proposal for pure JSON file storage, mandating dual-write SQLite database storage for auditability and artifact hashing.
- **Why it matters**: Shaped the core data access architecture (`src/parity/db/`) to be fully traceable across pipeline stages.