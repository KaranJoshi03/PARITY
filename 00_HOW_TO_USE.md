# How I work on PARITY

## Roles (assign real models available to me today; verify current options)
- ARCHITECT: strongest reasoning model. Advice, critique, design options. Never decides.
- BUILDER: fast coding model. Implements exactly one scoped task per session.
- SKEPTIC: a model from a DIFFERENT family than the Builder. Reviews and attacks. Fixes nothing.
- I decide, verify results, and own every document. Agents write all code.

## Session protocol
1. New session per prompt. Paste SESSION OPENER first (in PARITY_PROMPTS.md).
2. Agent restates state; I say "go".
3. Agent works. I read outputs (not just summaries). I ask for the exact command to run and the real output.
4. Push back on anything unverified, vague, or too confident & state WHY.
5. Close with CLOSE-OUT prompt (updates STATE.md, drafts ledger entries).
6. Export the full session to transcripts/phaseNN_task/. Scrub secrets only. Never edit anything else.

## Phase loop
IMPLEMENT -> TEST -> REVIEW (Skeptic) -> I verify the Skeptic's claims -> fix -> decision entry -> snapshot.

## Gate rule
A phase is done only when: tests were run and I saw real output; Skeptic findings were each marked real/false by me; decisions/ has an entry; STATE.md is current; a snapshot exists.

## What I never do
- Accept "all tests pass" without the output.
- Fake a mistake or a correction for the transcript.
- Let an agent change interfaces in CONTRACTS.md without my explicit approval.
- Report a number that is not in eval/results/.