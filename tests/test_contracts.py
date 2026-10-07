"""Tests for PARITY contract objects (CONTRACTS.md data classes).

Validates:
- Strict validation: unknown fields rejected, missing required fields rejected,
  wrong types rejected, invalid enum values rejected.
- Field value invariants (e.g. TestStrength score == killed/total).
- JSON serialization round-tripping (to_dict / from_dict / to_json / from_json).
"""

import json
import pytest

from parity.contracts import (
    CaptureRecord,
    ContractError,
    Divergence,
    MigrationResult,
    ModuleReport,
    TestStrength,
)


# ---------------------------------------------------------------------------
# CaptureRecord
# ---------------------------------------------------------------------------

class TestCaptureRecordContract:
    def test_valid(self, valid_capture_record_dict):
        rec = CaptureRecord.from_dict(valid_capture_record_dict)
        assert rec.module == "legacy_csv_parser"
        assert rec.entry_point == "parse_rows"
        assert rec.deterministic is True
        assert rec.to_dict() == valid_capture_record_dict

    def test_unknown_field_rejected(self, valid_capture_record_dict):
        valid_capture_record_dict["extra_field"] = "bad"
        with pytest.raises(ContractError, match="unknown fields"):
            CaptureRecord.from_dict(valid_capture_record_dict)

    def test_missing_field_rejected(self, valid_capture_record_dict):
        del valid_capture_record_dict["module"]
        with pytest.raises(ContractError, match="missing required fields"):
            CaptureRecord.from_dict(valid_capture_record_dict)

    def test_invalid_outputs_keys(self, valid_capture_record_dict):
        valid_capture_record_dict["outputs"] = {"return": 1, "stdout": ""}
        with pytest.raises(ContractError, match="outputs: key mismatch"):
            CaptureRecord.from_dict(valid_capture_record_dict)

    def test_invalid_side_effect_flags(self, valid_capture_record_dict):
        valid_capture_record_dict["side_effect_flags"]["time"] = "not_bool"
        with pytest.raises(ContractError, match="side_effect_flags.time: expected bool"):
            CaptureRecord.from_dict(valid_capture_record_dict)

    def test_json_roundtrip(self, valid_capture_record_dict):
        rec = CaptureRecord.from_dict(valid_capture_record_dict)
        json_str = rec.to_json()
        rec2 = CaptureRecord.from_json(json_str)
        assert rec == rec2


# ---------------------------------------------------------------------------
# MigrationResult
# ---------------------------------------------------------------------------

class TestMigrationResultContract:
    def test_valid(self, valid_migration_result_dict):
        res = MigrationResult.from_dict(valid_migration_result_dict)
        assert res.backend == "ollama"
        assert res.parse_ok is True

    def test_invalid_type(self, valid_migration_result_dict):
        valid_migration_result_dict["duration_ms"] = "slow"
        with pytest.raises(ContractError, match="duration_ms: expected number"):
            MigrationResult.from_dict(valid_migration_result_dict)

    def test_json_roundtrip(self, valid_migration_result_dict):
        res = MigrationResult.from_dict(valid_migration_result_dict)
        res2 = MigrationResult.from_json(res.to_json())
        assert res == res2


# ---------------------------------------------------------------------------
# Divergence
# ---------------------------------------------------------------------------

class TestDivergenceContract:
    def test_valid(self, valid_divergence_dict):
        div = Divergence.from_dict(valid_divergence_dict)
        assert div.category == "type"
        assert div.severity == "high"

    def test_invalid_category(self, valid_divergence_dict):
        valid_divergence_dict["category"] = "random_category"
        with pytest.raises(ContractError, match="category: 'random_category' not in"):
            Divergence.from_dict(valid_divergence_dict)

    def test_invalid_severity(self, valid_divergence_dict):
        valid_divergence_dict["severity"] = "critical"
        with pytest.raises(ContractError, match="severity: 'critical' not in"):
            Divergence.from_dict(valid_divergence_dict)

    def test_json_roundtrip(self, valid_divergence_dict):
        div = Divergence.from_dict(valid_divergence_dict)
        div2 = Divergence.from_json(div.to_json())
        assert div == div2


# ---------------------------------------------------------------------------
# TestStrength
# ---------------------------------------------------------------------------

class TestTestStrengthContract:
    def test_valid(self, valid_test_strength_dict):
        ts = TestStrength.from_dict(valid_test_strength_dict)
        assert ts.score == 0.8
        assert ts.mutants_killed == 8

    def test_mismatched_score_rejected(self, valid_test_strength_dict):
        valid_test_strength_dict["score"] = 0.99
        with pytest.raises(ContractError, match="score: 0.99 != killed/total"):
            TestStrength.from_dict(valid_test_strength_dict)

    def test_killed_greater_than_total_rejected(self, valid_test_strength_dict):
        valid_test_strength_dict["mutants_killed"] = 12
        valid_test_strength_dict["score"] = 1.2
        with pytest.raises(ContractError, match="mutants_killed .* > mutants_total"):
            TestStrength.from_dict(valid_test_strength_dict)

    def test_zero_total_mutants(self, valid_test_strength_dict):
        valid_test_strength_dict["mutants_total"] = 0
        valid_test_strength_dict["mutants_killed"] = 0
        valid_test_strength_dict["score"] = 0.0
        valid_test_strength_dict["insufficient"] = True
        ts = TestStrength.from_dict(valid_test_strength_dict)
        assert ts.score == 0.0
        assert ts.insufficient is True



# ---------------------------------------------------------------------------
# ModuleReport
# ---------------------------------------------------------------------------

class TestModuleReportContract:
    def test_valid(self, valid_module_report_dict):
        rep = ModuleReport.from_dict(valid_module_report_dict)
        assert rep.verdict == "SAFE"

    def test_invalid_verdict(self, valid_module_report_dict):
        valid_module_report_dict["verdict"] = "PASSED"
        with pytest.raises(ContractError, match="verdict: 'PASSED' not in"):
            ModuleReport.from_dict(valid_module_report_dict)

    def test_json_roundtrip(self, valid_module_report_dict):
        rep = ModuleReport.from_dict(valid_module_report_dict)
        rep2 = ModuleReport.from_json(rep.to_json())
        assert rep == rep2
