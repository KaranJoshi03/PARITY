# PARITY Evaluation Pre-registration
Date written: {{4th Oct 2026}}   Written before any evaluation run: yes

## Hypotheses
H1: Arm C (LLM + PARITY) catches a higher share of silent regressions than Arm B (unverified LLM) and Arm A (2to3).
H2: False-SAFE rate of Arm C is below {{DECIDE %}}.
H3: PARITY's added cost per module is acceptable (time compute reported, no money cost).

## Corpus
Source: public Python packages with a Python-2-only release followed by a release that supports Python 3 (human migration as reference). Sources and licenses recorded per module. {{DECIDE exact source(s), verified by the agent in Phase 12}}
Inclusion: pure-Python module, 30 to 400 lines, importable, license permits use, at least one callable entry point, no network or GUI dependence.
Exclusion (decided now, applied mechanically): C extensions, heavy I/O or network, modules whose py2 behavior is nondeterministic and cannot be controlled, unsupported dependencies. Every exclusion logged with reason.
Target sample: {{DECIDE, aim 30 to 60}}. Selection rule: all modules meeting criteria from a pre-listed set of sources, in sorted order, first N. No cherry-picking.

## Arms
A: 2to3 only. B: LLM migration, no verification, verdict taken as "accept". C: LLM migration + PARITY verdicts.
Models: {{DECIDE exact local/free models, fixed for the whole run, temperature fixed}}.

## Ground truth
A module has a true silent regression if the LLM migration diverges from the original py2 behavior on an input where the human py3 migration does NOT diverge. If the human version also diverges, it is an intended change (excluded from counts, reported).
Ground-truth inputs: captured inputs + generated inputs + a held-out set not used for verdicts: {{DECIDE size}}.

## Metrics
M1 silent-regression catch rate (Arm C flags / true regressions). M2 false-SAFE rate. M3 false-BLOCK rate. M4 agreement with human migration. M5 time per module. M6 share of modules ending RISKY (report; do not hide).

## Analysis
Bootstrap 95% confidence intervals; paired comparison between arms per module. Report all crashes, timeouts, parse failures. No post-hoc metric changes. Any deviation recorded as a dated addendum.

## Thresholds
SAFE test-strength threshold: {{DECIDE, initial 0.70}}.

## Threats to validity (write honestly, extend after red team)
Sample not representative; held-out inputs share bias with generated inputs; weak open models; module selection tied to packages that eventually migrated; comparator choices influence results; possible leakage if the LLM saw the human migration in training.