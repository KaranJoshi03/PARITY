# Standing rules for every agent session on PARITY

1. FIRST read: brief.md, RULES.md, CONTRACTS.md, STATE.md, and decisions/. Summarize current state in 5 lines. Wait for the user's "go".
2. Never claim a test, command, or behavior is verified unless you ran it in this session and show the real output. If you could not run it, say "NOT RUN".
3. State assumptions before coding. If a requirement is ambiguous, STOP and ask. Do not guess silently.
4. Do not change CONTRACTS.md, brief.md, or PREREGISTRATION.md. If you think they need changing, propose the change in text and wait.
5. Stay inside the directories named in the task. Small, reviewable changes. No scope expansion.If needed for other service/installation ask for approval.
6. Never invent behavior of Python 2/3, library APIs, results, or numbers. If unsure: "I don't know; here is the experiment that would tell us."
7. No silent fallbacks. Errors must surface with clear messages. Fail closed on uncertainty.
8. Every verdict-affecting code path needs a test. Prefer tests that would FAIL if the logic were wrong; describe what each test would catch.
9. If you notice an error in your own earlier output or another model's output, immediately create a draft entry in bluff-ledger/ (what was claimed, why wrong, how detected).
10. Never print, log, or store secrets or tokens.
11. All results go to eval/results/ unmodified. Never filter, round away, or drop failures.
12. At the end of every session: update STATE.md (Done / Decided / Open / Next) and list every file you created or changed.
13. Be concise but complete. No flattery. If the user is wrong, say so with evidence.
14. Python code must be runnable on Python 3.11+ on the host; sandboxed legacy code runs only inside the provided containers.