"""Shared fixtures for PARITY tests."""

import pytest


# ---------------------------------------------------------------------------
# Valid dicts for every contract object (reusable across test modules)
# ---------------------------------------------------------------------------

VALID_SIDE_EFFECT_FLAGS = {
    "time": False,
    "random": False,
    "file_io": False,
    "network": False,
    "env": False,
    "global_state": False,
}

VALID_OUTPUTS = {
    "return": {"t": "int", "v": 42},
    "exception": None,
    "stdout": "",
    "stderr": "",
}


@pytest.fixture
def valid_capture_record_dict():
    """Minimal valid CaptureRecord dict per CONTRACTS.md."""
    return {
        "module": "legacy_csv_parser",
        "entry_point": "parse_rows",
        "input": {"args": [{"t": "str", "v": "hello"}], "kwargs": {}},
        "outputs": dict(VALID_OUTPUTS),
        "duration_ms": 12.5,
        "runs": 3,
        "deterministic": True,
        "non_determinism_reason": None,
        "side_effect_flags": dict(VALID_SIDE_EFFECT_FLAGS),
        "lossy": False,
    }


@pytest.fixture
def valid_migration_result_dict():
    """Minimal valid MigrationResult dict per CONTRACTS.md."""
    return {
        "module": "legacy_csv_parser",
        "backend": "ollama",
        "model_name": "codellama",
        "parameters": {"temperature": 0.0},
        "prompt": "Migrate this module to Python 3...",
        "raw_output": "def parse_rows():\n    pass\n",
        "parsed_code": "def parse_rows():\n    pass\n",
        "parse_ok": True,
        "parse_error": None,
        "timestamp": "2026-10-04T18:00:00Z",
        "duration_ms": 1500.0,
    }


@pytest.fixture
def valid_divergence_dict():
    """Minimal valid Divergence dict per CONTRACTS.md."""
    return {
        "module": "legacy_csv_parser",
        "entry_point": "parse_rows",
        "input": {"args": [{"t": "int", "v": 6}], "kwargs": {}},
        "py2_behavior": {"return": {"t": "int", "v": 3}},
        "py3_behavior": {"return": {"t": "float", "v": 3.0}},
        "category": "type",
        "comparator_rule_applied": "R2",
        "severity": "high",
    }


@pytest.fixture
def valid_test_strength_dict():
    """Minimal valid TestStrength dict per CONTRACTS.md."""
    return {
        "mutants_total": 10,
        "mutants_killed": 8,
        "score": 0.8,
        "mutation_operators_used": ["swap_division", "remove_list_wrap"],
        "survivors": [{"operator": "swap_encode", "line": 42}],
        "insufficient": False,
    }


@pytest.fixture
def valid_module_report_dict():
    """Minimal valid ModuleReport dict per CONTRACTS.md."""
    return {
        "module": "legacy_csv_parser",
        "verdict": "SAFE",
        "evidence": [{"type": "comparison", "path": "comparisons/legacy_csv_parser__parse_rows__abc123.json"}],
        "test_strength": {
            "mutants_total": 10,
            "mutants_killed": 8,
            "score": 0.8,
            "mutation_operators_used": ["swap_division"],
            "survivors": [],
            "insufficient": False,
        },
        "flags": [],
        "human_migration_comparison": None,
        "timings": {"capture_ms": 100, "migrate_ms": 1500, "diffcheck_ms": 200},
    }
