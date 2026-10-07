# PARITY: Concrete Failure Scenarios

---

## Architecture A (Pipeline-of-Files): The Stale Capture Problem

### The module
`legacy_csv_parser.py` — a Python 2 module that reads CSV data, accumulates rows into a `dict`, and returns a summary. Keys are byte strings in py2. The module has 4 entry points.

### What happens
1. **Phase 1 (Tuesday)**: You run capture against all 4 entry points. Capture writes 38 JSON files to `capture_records/`. Everything is clean.
2. **Phase 2 (Thursday)**: You realize your input generator missed edge cases for empty-string keys. You re-run capture for *only* `parse_rows()` — the entry point you suspect is risky. The generator now produces 15 new capture files including the empty-key case.
3. You **forget to delete** the 12 old capture files for `parse_rows()`. The directory now has both old captures (without empty-key inputs) and new captures (with them).
4. **Diffcheck runs on all files in the directory**. It picks up both old and new captures. For the old captures, the migrated py3 code happens to match (the empty-key divergence isn't exercised). The new captures *do* catch the divergence — but there are also "duplicate" old captures for the same inputs that show "match."
5. **The divergence is detected** in this case — but now imagine a slightly different scenario: you re-ran capture with a *different* input generator that replaced the old inputs entirely (new random seed). The old captures for `parse_rows()` still exist. Diffcheck runs the old inputs against py3 and sees no divergence. The new inputs that *would* have caught it were never generated because you ran a different generator version. The 15 new files look clean. The 12 stale files look clean. Verdict: **SAFE**.
6. The actual module silently changes behavior on `b""` as a dict key (py2 `""` and `b""` are the same type; py3 they're not). You shipped a false SAFE.

### Why this architecture makes it likely
Pipeline-of-Files has **no concept of "which run produced which file."** Files accumulate in directories. There's no manifest, no run ID, no foreign key linking a capture to the generator version that produced it. Staleness is invisible. The fail-closed contract says "missing signal → can't be SAFE," but stale files aren't *missing* — they're *present and wrong*. The fail-closed design doesn't protect you here.

### How you'd notice
You probably wouldn't, unless you manually diffed the file list against a log. There is no log.

---

## Architecture B (SQLite Library): The In-Process Poisoning

### The module
`legacy_config.py` — a Python 2 module that reads a config file using `execfile()` (py2 built-in), sets module-level globals, and exposes `get_setting(key)`. The LLM migration replaces `execfile()` with `exec(open(...).read())` and changes the globals handling.

### What happens
1. Capture runs in the py2 container. Clean. Records stored in SQLite via import.
2. Migration runs. The LLM produces py3 code that *looks* correct.
3. **Diffcheck runs in-process.** It does `importlib.import_module("legacy_config_migrated")`. The migrated module's top-level code runs `exec(open("config.ini").read())` at import time.
4. The `exec()` call executes arbitrary code from `config.ini` **inside the PARITY process**. In the test fixture, `config.ini` is benign. But the `exec()` also sets `sys.path`, modifies `os.environ`, and writes to a temp file.
5. These side effects **contaminate the PARITY process itself**. `sys.path` now includes a directory the migrated module added. `os.environ` has new values. When diffcheck proceeds to the *next* module in the same process, that module's behavior is affected by the polluted environment.
6. Module N+1 (`legacy_network_utils.py`) reads `os.environ["PROXY_HOST"]` — a value that was set by module N's side effect, not by your test fixture. Diffcheck sees the py3 output matches what py2 produced (because py2 also had `execfile()` side effects, but in a *different* order because the py2 container ran modules in isolation). The comparison is now **apples to oranges**, but the values happen to match on this run. Verdict: **SAFE**.
7. On a different machine, or with a different module ordering, the environment pollution is different, and the verdict flips to BLOCKED. The result is **non-reproducible**, violating S3.

### Why this architecture makes it likely
Architecture B runs everything in one Python 3 process. There is **no isolation boundary** between PARITY's own code and the migrated code it's testing. Any migrated module that has import-time side effects (common in legacy code — `execfile`, global initialization, `os.environ` mutation, `sys.path` hacking, `logging.basicConfig()`) can corrupt the process. The SQLite database itself could even be affected if migrated code opens a connection to the same file.

Legacy Python 2 code is *full* of import-time side effects. This isn't an edge case — it's the common case for the kind of code PARITY targets.

### How you'd notice
You might notice if you re-ran the same module in isolation and got a different verdict. But if you only run the full corpus once (as the eval harness does), you'd never see the discrepancy. The SQLite DB records the "result" without recording the process state at the time.

---

## Architecture C (Event-Sourced Log): The Reducer Version Skew

### The module
`legacy_math_utils.py` — a Python 2 module with `safe_divide(a, b)` that uses Python 2 integer division (`/` on ints → int). The LLM migration adds `from __future__ import division` but misses one code path where integer division was intended.

### What happens
1. **Run 1**: Capture produces `CaptureEvent`s with 20 inputs. Diffcheck appends `ComparisonEvent`s — 18 match, 2 diverge (integer division path). `VerdictEvent`: BLOCKED. Correct.
2. You adjust the input generator to be more thorough. **Run 2**: New `CaptureEvent`s (version 2) appended with 35 inputs. But you *also* tweak the comparator to handle a different R3 float-tolerance issue you found in another module. The new comparator version is `2.1`.
3. Diffcheck Run 2 uses comparator `2.1` and the 35 new inputs. It appends 35 `ComparisonEvent`s (version 2). The integer-division divergence is caught in 3 of the 35 inputs. `VerdictEvent` v2: BLOCKED. Still correct.
4. **You realize comparator 2.1 has a bug on a different module.** You roll back to comparator `2.0` and re-run diffcheck. But you only re-run it for the module where the bug was found — not for `legacy_math_utils.py`.
5. The `legacy_math_utils.py` log now has: v1 captures, v2 captures, v1 comparisons (from comparator 2.0), v2 comparisons (from comparator 2.1). **The reducer takes the "latest version" of each event type.** The latest `ComparisonEvent`s are v2, produced by comparator 2.1.
6. Later, you discover that comparator 2.1 had a *second* bug: it was silently treating `int` vs `float` comparison as equal (breaking R3) when the float happened to be a whole number like `3.0`. The integer-division divergence in `safe_divide(6, 2)` returned `3` (int, py2) vs `3.0` (float, py3). Comparator 2.1 called this "equal." Comparator 2.0 would have called it a divergence.
7. You rolled back to comparator 2.0 for the *other* module but **never re-ran `legacy_math_utils.py` with 2.0**. The log still has v2 ComparisonEvents from the buggy comparator. The reducer uses them. `VerdictEvent` v2 says BLOCKED only because of the other 2 divergent inputs — but if those inputs happened to not be generated in a future run, the verdict would flip to SAFE based on buggy comparison data.
8. **The fundamental problem**: the log faithfully records *what happened*, but the reducer has no way to know that the comparator version used for v2 events has since been declared buggy. There is no mechanism to invalidate events produced by a known-bad tool version.

### Why this architecture makes it likely
Event sourcing's strength — immutability — becomes a weakness when the *tool that produced an event* is later found to be wrong. In Architecture A, you'd just delete the stale files and re-run (though staleness is still a risk, it's a *simpler* risk). In Architecture B, you'd UPDATE the rows. In Architecture C, you can't delete or update — you can only append. Invalidation requires either:
- A new `InvalidationEvent` type (adds complexity, and the reducer must handle it correctly), or
- Deleting and regenerating the log (which destroys the audit trail — the very thing C exists for).

The "latest version" heuristic sounds simple but breaks down when different event types are produced at different times by different tool versions. **Version skew between events in the same log** is a subtle, hard-to-detect state that the reducer must handle correctly. Getting this wrong is a direct path to false SAFE.

### How you'd notice
You'd need to cross-reference each ComparisonEvent's metadata (comparator version) against your changelog of which comparator versions had bugs. This is a manual, error-prone process. The log has the data to do it, but nothing forces you to check.

---

## Which failure set worries me most

**Architecture B's in-process poisoning worries me most.** Here's why:

1. **It's not a bug — it's a structural property.** A and C's failure scenarios involve operational mistakes (stale files, version skew) that can be mitigated with discipline, tooling, or checklists. B's failure is inherent to the architecture: running untrusted migrated code in-process *will* cause side effects in legacy code, and you can't fix it without changing the architecture to use subprocess isolation — at which point you've moved toward A or C anyway.

2. **It's invisible.** Stale files (A) can be caught by a manifest check. Version skew (C) can be caught by logging tool versions in events. But process-state pollution in B leaves no trace in the SQLite database. The DB records the *result* of a comparison, not the `sys.path` or `os.environ` at the time. You'd need full process-state snapshots to detect it, which is impractical.

3. **It compounds across modules.** A's stale-file problem and C's version-skew problem are per-module. B's pollution crosses module boundaries within a single eval run. The effect depends on *module ordering*, making it non-reproducible and violating success criterion S3.

4. **Legacy code is the worst case.** Clean, modern Python rarely has import-time side effects. Legacy Python 2 code — the exact target of PARITY — is full of `execfile`, global `import`-time initialization, `sys.path` hacking, and environment mutation. B's weakness aligns perfectly with the input domain.

A's stale-file problem is real but detectable (add a manifest). C's version-skew problem is real but addressable (log tool versions, add invalidation events). B's in-process poisoning is structural and requires architectural change to fix.

That said: A and C's failure scenarios are more *likely to happen silently without anyone noticing*. B's failure is more likely to produce visibly weird results that trigger investigation. A quiet false SAFE (A or C) might be worse than a loud, confusing non-reproducibility (B), depending on whether you value "never wrong" over "never silently wrong."

I do not know which trade-off you prefer. That's a judgment call only you can make.
