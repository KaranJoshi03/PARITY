# PARITY Contracts (binding; agents may not change these without approval)

## Definitions
- **Entry point**: a function/callable in a py2 module chosen for behavioral comparison.
- **Capture record**: one execution of an entry point under py2 with a serialized input and observed outputs.
- **Observable behavior**: return value (type-tagged), raised exception (class + message), stdout, stderr, and, for script/process executions, exit status.
- **Behavioral divergence**: for the same input, observable behavior of the migrated py3 module differs from the recorded py2 behavior after applying the comparator rules below.
- **Silent regression**: a divergence in a migrated module that did not cause a syntax/import error, i.e. the migration "looks fine" but behaves differently.
- **Intended change**: a divergence where the human-written py3 version also differs from the original py2 (the maintainers changed behavior on purpose). Excluded from regression counts but reported.
- **Test strength**: share of injected migration-relevant faults (mutants) that the capture+generated inputs detect.
- **False SAFE**: verdict SAFE on a module that has at least one true silent regression.

## Serialization (type-tagged JSON)
Every value is stored as {"t": <type tag>, "v": <value>}. Tags: none, bool, int, long, float, str (py2 byte string), unicode, bytes3 (py3 bytes), str3 (py3 text), list, tuple, dict (ordered pairs list), set (sorted list with ordering note), exception, repr_fallback.
Anything that cannot be serialized faithfully must be tagged repr_fallback AND the record flagged lossy.

## CaptureRecord
module, entry_point, input (serialized args/kwargs), outputs (return, exception, stdout, stderr), duration_ms, runs (3), deterministic (bool), non_determinism_reason, side_effect_flags (time, random, file_io, network, env, global_state), lossy (bool).

## MigrationResult
module, backend, model_name, parameters, prompt, raw_output, parsed_code, parse_ok (bool), parse_error, timestamp, duration_ms.

## Divergence
module, entry_point, input, py2_behavior, py3_behavior, category (value | type | exception_type | exception_message | stdout | ordering | encoding | numeric | timing), comparator_rule_applied, severity (low | high).

## Comparator rules (explicit, configurable, each logged when applied)
- R1 str/unicode/str3 text equality: equal only if the decoded text is identical; bytes vs text is NEVER equal.
- R2 int vs long: equal if numerically equal.
- R3 floats: equal within tolerance set in config (default exact; relaxation must be recorded).
- R4 dict/set ordering: py2 order is not guaranteed; compare as sets/maps AND flag "order-dependent" if output text depends on order.
- R5 exception: class name AND message must match unless a rule explicitly maps py2 class names to py3.
- R6 timing differences alone never count as divergence; reported separately.
Default stance: when a rule is unclear, count it as divergence.

## TestStrength
mutants_total, mutants_killed, score = killed/total, mutation_operators_used, survivors (list), insufficient (bool).

## Verdict (fail closed)
| Condition | Max verdict |
|---|---|
| Any divergence (excluding documented intended change) | BLOCKED |
| Any internal error, timeout, or unparsed migration | RISKY or lower |
| Non-determinism unresolved | RISKY or lower |
| Lossy serialization on a verdict-relevant input | RISKY or lower |
| Test strength below threshold (initial 0.70, final value fixed in PREREGISTRATION.md) | RISKY or lower |
| Unsupported construct detected (flagged list) | RISKY or lower |
| All signals present and passing | SAFE |
Removing, corrupting, or timing out any signal can never raise a verdict.

## ModuleReport
module, verdict, evidence (list with links to captured records and divergences), test_strength, flags, human_migration_comparison (if available), timings.