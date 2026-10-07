-- Parity pipeline SQLite schema with audit & run‑locking
PRAGMA foreign_keys = ON;

-- ==============================================================
-- 0. Run‑level metadata
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK(status IN ('in_progress','complete','failed')),
    manifest    TEXT NOT NULL,
    locked      INTEGER NOT NULL DEFAULT 0   -- 0 = mutable, 1 = locked after completion
);

-- ==============================================================
-- 1. Capture records
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS captures (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    module           TEXT NOT NULL,
    entry_point      TEXT NOT NULL,
    input_hash       TEXT NOT NULL,
    input_json       TEXT NOT NULL,
    outputs_json     TEXT NOT NULL,
    artifact_hash    TEXT NOT NULL,
    inserted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    UNIQUE(run_id, module, entry_point, input_hash)
);

-- ==============================================================
-- 2. Migration results
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS migrations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    module           TEXT NOT NULL,
    backend          TEXT NOT NULL,
    model_name       TEXT NOT NULL,
    raw_output       TEXT NOT NULL,
    parsed_code      TEXT NOT NULL,
    parse_ok         INTEGER NOT NULL CHECK(parse_ok IN (0,1)),
    parse_error      TEXT,
    timestamp        TEXT NOT NULL,
    duration_ms      REAL NOT NULL,
    artifact_hash    TEXT NOT NULL,
    inserted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    UNIQUE(run_id, module, backend, model_name)
);

-- ==============================================================
-- 3. Divergences
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS divergences (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                 TEXT NOT NULL,
    capture_id             INTEGER NOT NULL,
    migration_id           INTEGER NOT NULL,
    category               TEXT NOT NULL,
    comparator_rule        TEXT NOT NULL,
    severity               TEXT NOT NULL CHECK(severity IN ('low','high')),
    py2_behavior           TEXT NOT NULL,
    py3_behavior           TEXT NOT NULL,
    artifact_hash          TEXT NOT NULL,
    inserted_at            TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id)    REFERENCES runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY(capture_id)   REFERENCES captures(id) ON DELETE CASCADE,
    FOREIGN KEY(migration_id) REFERENCES migrations(id) ON DELETE CASCADE
);

-- ==============================================================
-- 4. Comparator log (extra metadata for each divergence)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comparator_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    divergence_id   INTEGER NOT NULL,
    rule_applied     TEXT NOT NULL,
    details          TEXT,
    inserted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id)    REFERENCES runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY(divergence_id) REFERENCES divergences(id) ON DELETE CASCADE
);

-- ==============================================================
-- 5. Mutation testing results
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mutations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    module           TEXT NOT NULL,
    mutant_id        TEXT NOT NULL,
    operator         TEXT NOT NULL,
    mutated_code     TEXT NOT NULL,
    killed           INTEGER NOT NULL CHECK(killed IN (0,1)),
    artifact_hash    TEXT NOT NULL,
    inserted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    UNIQUE(run_id, module, mutant_id)
);

-- ==============================================================
-- 6. Verdicts (final ModuleReport)
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verdicts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT NOT NULL,
    module           TEXT NOT NULL,
    verdict          TEXT NOT NULL CHECK(verdict IN ('SAFE','RISKY','BLOCKED')),
    flags            TEXT,
    report_json      TEXT NOT NULL,
    artifact_hash    TEXT NOT NULL,
    inserted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    UNIQUE(run_id, module)
);

-- ==============================================================
-- 7. Metric definitions – immutable reference table
-- --------------------------------------------------------------
-- 7. Metric definitions – immutable reference table
CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_name   TEXT PRIMARY KEY,
    description   TEXT NOT NULL,
    formula       TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 8. Metric results – captured per run, immutable after lock
CREATE TABLE IF NOT EXISTS metric_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    metric_name   TEXT NOT NULL,
    value         REAL NOT NULL,
    notes         TEXT,
    inserted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY(metric_name) REFERENCES metric_definitions(metric_name) ON DELETE RESTRICT,
    UNIQUE(run_id, metric_name)
);

-- 9. Analysis adjustment log – records any post‑hoc changes
CREATE TABLE IF NOT EXISTS analysis_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    action        TEXT NOT NULL,
    details       TEXT,
    timestamp     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

-- 10. Audit log – any attempt to modify a locked run is recorded
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT,
    table_name    TEXT NOT NULL,
    operation     TEXT NOT NULL,
    timestamp     TEXT NOT NULL DEFAULT (datetime('now')),
    details       TEXT
);

-- ==============================================================
-- Triggers to prevent writes to a locked run (INSERT already defined above)
-- --------------------------------------------------------------
-- Prevent UPDATE on metric_results when run is locked
CREATE TRIGGER IF NOT EXISTS prevent_metric_result_update
BEFORE UPDATE ON metric_results
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'metric_results', 'UPDATE_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot update metric result');
END;

-- Prevent INSERT on analysis_log after lock (already covered by generic insert triggers, but add explicit for clarity)
CREATE TRIGGER IF NOT EXISTS prevent_analysis_log_insert
BEFORE INSERT ON analysis_log
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'analysis_log', 'INSERT_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot insert analysis log');
END;

-- Prevent UPDATE on analysis_log after lock
CREATE TRIGGER IF NOT EXISTS prevent_analysis_log_update
BEFORE UPDATE ON analysis_log
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'analysis_log', 'UPDATE_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot update analysis log');
END;

-- Existing triggers for captures, migrations, divergences, mutations, verdicts remain unchanged


-- ==============================================================
-- Triggers to prevent writes to a locked run
-- --------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS prevent_capture_insert
BEFORE INSERT ON captures
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'captures', 'INSERT_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot insert capture');
END;

CREATE TRIGGER IF NOT EXISTS prevent_migration_insert
BEFORE INSERT ON migrations
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'migrations', 'INSERT_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot insert migration');
END;

CREATE TRIGGER IF NOT EXISTS prevent_divergence_insert
BEFORE INSERT ON divergences
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'divergences', 'INSERT_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot insert divergence');
END;

CREATE TRIGGER IF NOT EXISTS prevent_mutation_insert
BEFORE INSERT ON mutations
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'mutations', 'INSERT_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot insert mutation');
END;

CREATE TRIGGER IF NOT EXISTS prevent_verdict_insert
BEFORE INSERT ON verdicts
FOR EACH ROW
WHEN (SELECT locked FROM runs WHERE run_id = NEW.run_id) = 1
BEGIN
    INSERT INTO audit_log (run_id, table_name, operation, details)
    VALUES (NEW.run_id, 'verdicts', 'INSERT_BLOCKED', 'Run is locked');
    SELECT RAISE(ABORT, 'Run is locked – cannot insert verdict');
END;

-- ==============================================================
-- Indexes for fast look‑ups
-- --------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_captures_module      ON captures(module);
CREATE INDEX IF NOT EXISTS idx_migrations_module    ON migrations(module);
CREATE INDEX IF NOT EXISTS idx_divergences_module   ON divergences(module);
CREATE INDEX IF NOT EXISTS idx_mutations_module     ON mutations(module);
CREATE INDEX IF NOT EXISTS idx_verdicts_module      ON verdicts(module);
