# STATE

## Done
- Package setup and config (`pyproject.toml` pointing to `src/`, editable install verified).
- Type-tagged JSON serializer (`src/parity/serializer.py`) with full 15-tag schema and payload validation.
- Central config module (`src/parity/config.py`) matching `CONTRACTS.md` defaults.
- Contract data classes (`src/parity/contracts.py`) for `CaptureRecord`, `MigrationResult`, `Divergence`, `TestStrength`, and `ModuleReport` with strict validation and fail-closed rules.
- Project snapshot tool (`src/parity/snapshot.py`, `parity-snapshot`) with secret directory and extensionless key exclusions.
- Sandboxed execution layer (`src/parity/sandbox.py`, `docker/Dockerfile.py2`, `docker/Dockerfile.py3`, `docker/entrypoint.py`) with network, file system, process, and resource isolation.
- Unit test suite (`tests/` with 102 passing unit tests).
- 20 fixture triples under `fixtures/` (01 to 20) with real output verification in each `fixture.md`.
- Fixtures meta-test suite (`tests/test_fixtures_meta.py` with 60/60 passing tests across all 20 fixtures).
- Fixtures audit report generated at `eval/results/fixtures_meta_test_failures.md` (0 failures).
- Language-semantics divergence taxonomy developed (5 dominant root causes + unrepresented behaviors + 8 proposed hard fixtures).
- Bluff ledger updated with entries 005 and 006 (`bluff-ledger/005-...`, `bluff-ledger/006-...`).

## Decided
- Enhanced Architecture A+ (pipeline-of-files, process isolation, immutable per-run directories, strict JSON contracts, fail-closed verdict calculation).
- Docker flags: `--network none`, `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=64m`, `--user 1000:1000`, `--cpus=1.0`, `--memory=512m`, `--pids-limit=64`, `PYTHONHASHSEED=0`, `LC_ALL=C.UTF-8`, `LANG=C.UTF-8`, `TZ=UTC`.
- Fixture design rule: Tests must assert observable runtime contracts (e.g. `isinstance(x, int)` replacing `isinstance(x, (int, long))`, or `list(range(n))` replacing `list(xrange(n))`) so that `original_py2` and `correct_py3` match on exposing inputs while unmigrated code diverges.
- Divergence taxonomy codes standardized (`ROOT-1` through `ROOT-5` and subcategories `SEM-*`) for systematic categorization across reports and bluff-ledger.

## Open questions
- Automatic Docker Desktop daemon startup handling when running on Windows hosts without background service auto-start.

## Risks noticed
- Microarchitectural floating-point variations across hardware architectures remain non-deterministic.
- Execution timing measurements (`duration_ms`) vary slightly depending on OS process scheduling.
- Subtly wrong Py3 migrations often pass naive test inputs and diverge only on rare/edge inputs (e.g. float inputs to `//`, non-ASCII byte buffers).

## Next
- Phase 1: Implement Stage 1 (py2 capture module, input generator, and determinism check runner).