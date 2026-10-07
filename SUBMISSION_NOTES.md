# PARITY Submission Notes

## How to Run

### Run Full Test Suite
```bash
pytest -q
```

### Dry-Run Evaluation Harness
```bash
python -m eval.harness --dry-run --modules 3
```

## Folder Architecture Map
- `src/parity/`: Core engine implementation (Capture, Migrate, Verify, Verdict, Database).
- `eval/`: Evaluation harness, corpus manifests, and benchmark runner.
- `eval/results/`: Raw output JSON files for Arm A, Arm B, Arm C, and human reference migrations.
- `transcripts/`: Step-by-step logs of LLM agent execution with `INDEX.md`.
- `decisions/`: Architecture decision records (ADRs).
- `bluff-ledger/`: Audit trail of model over-confidence and errors.
- `reviews/`: Hostile reviewer findings (`review_pre_run.md`, `post_fix.md`).

## Models & Roles
- **Primary Agent**: Gemini 3.6 Flash / GPT-OSS 120B acting as Senior Implementation Engineer and Data Analyst.
- **Hostile Reviewer Agent**: Adversarial auditor looking for contract deviations and false-SAFE scenarios.

## Known Limitations
1. **Dynamic / C-Extension Limitations**: Pure Python static and dynamic tracing only; C-extensions and OS-level syscall side-effects are not captured.
2. **Lossy Repr Fallbacks**: Complex un-serializable objects fall back to string representations (`repr_fallback`), which can obscure minor internal state divergences.
