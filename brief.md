# PARITY: Brief

## 1. Problem
Large language models can rewrite legacy Python 2 code into Python 3 quickly. The output usually looks right and passes a casual read. But Python 2 and 3 differ in many subtle behaviors (integer division, bytes vs str, iteration order, sort rules, iterators vs lists, round, file encoding, exception text). A migration can compile, pass a few tests, and still silently change behavior. People maintaining old codebases cannot tell which AI-migrated modules are safe to accept without expensive manual review.

## 2. Who has this problem
Maintainers and small teams carrying legacy Python 2 code with limited tests and limited time, who are tempted to let AI do the migration. Their cost: either slow manual review of every module, or accepting silent regressions.

## 3. Why existing approaches fall short
- Rule-based tools (2to3 and similar) are deterministic but incomplete: they do not understand semantics such as division or bytes/str intent.
- Unverified LLM output is fluent and confident but has no evidence of behavioral equivalence.
- Existing test suites in legacy code are often thin, so "tests pass" is weak evidence.

## 4. What PARITY is
A verification layer, not a migrator. It records the real behavior of the original Python 2 module, runs the migrated Python 3 module against the same inputs plus generated inputs, measures whether the tests are strong enough to trust, and issues a per-module verdict (SAFE / RISKY / BLOCKED) with evidence. A human makes the final call. When evidence is missing, the verdict can never be SAFE (fail closed).

## 5. Success criteria (measured on a pre-registered corpus, results reported whether good or bad)
- S1: PARITY (Arm C) detects a materially higher share of silent regressions than unverified LLM migration (Arm B) and 2to3 (Arm A).
- S2: False-SAFE rate (module marked SAFE that actually regressed) is below a threshold set in PREREGISTRATION.md before running.
- S3: Every verdict is accompanied by reproducible evidence a human can read.
- S4: A working local demo plus a static results dashboard.
- S5: Complete, unedited AI session transcripts, a decision log, and a catalogue of AI failures I caught.

## 6. Constraints
Solo builder, zero budget, free tools only, local/open models where possible, built in weekends, all code written by AI agents under my direction, all documents owned by me.

## 7. Non-goals
Other languages; fully automatic migration; replacing human review; claiming real customers or users (there are none); security sandboxing beyond what a local demo needs.

## 8. Key risks (known upfront)
- The comparator may be too lenient (false SAFE).
- Captured inputs may not cover real behavior (weak tests).
- Bytes/str and int/long cross the py2/py3 boundary lossily.
- Legacy modules with I/O, time, randomness, global state resist deterministic capture.
- Small/weak open models may produce poor migrations (fine for the study, but must be reported).
- My sample may be unrepresentative of real legacy code.

## 9. Definitions
See CONTRACTS.md section "Definitions". They are binding.