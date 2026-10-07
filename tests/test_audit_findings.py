"""Tests verifying fixes for audit findings:
- Validation of payload structure in type-tagged serializer
- Non-determinism reason consistency in CaptureRecord
- repr_fallback tag enforcing lossy=True
- TestStrength score < 0.70 enforcing insufficient=True
- Fail-closed verdict checks in ModuleReport (cannot be SAFE with unsafe flags)
- Secret leakage prevention in snapshot (directories, extensionless SSH keys, case sensitivity)
"""

import pytest

from parity.contracts import CaptureRecord, ContractError, ModuleReport, TestStrength
from parity.serializer import SerializationError, validate_tagged_value
from parity.snapshot import should_exclude


def test_serializer_payload_validation():
    # Tag 'none' with non-None value must fail
    with pytest.raises(SerializationError, match="tag 'none' requires value None"):
        validate_tagged_value({"t": "none", "v": "not_none"})

    # Tag 'dict' with non-list value (CONTRACTS.md: ordered pairs list) must fail
    with pytest.raises(SerializationError, match="tag 'dict' requires ordered pairs list"):
        validate_tagged_value({"t": "dict", "v": {"a": 1}})

    # Tag 'int' with float or string value must fail
    with pytest.raises(SerializationError, match="tag 'int' requires int value"):
        validate_tagged_value({"t": "int", "v": "123"})


def test_capture_record_non_determinism_consistency(valid_capture_record_dict):
    # Non-deterministic record missing reason must fail
    valid_capture_record_dict["deterministic"] = False
    valid_capture_record_dict["non_determinism_reason"] = None
    with pytest.raises(ContractError, match="non_determinism_reason: required when deterministic is False"):
        CaptureRecord.from_dict(valid_capture_record_dict)

    # Deterministic record with reason must fail
    valid_capture_record_dict["deterministic"] = True
    valid_capture_record_dict["non_determinism_reason"] = "some reason"
    with pytest.raises(ContractError, match="non_determinism_reason: must be None when deterministic is True"):
        CaptureRecord.from_dict(valid_capture_record_dict)


def test_capture_record_lossy_repr_fallback_enforcement(valid_capture_record_dict):
    # repr_fallback present but lossy=False must fail per CONTRACTS.md § Serialization
    valid_capture_record_dict["outputs"]["return"] = {"t": "repr_fallback", "v": "<UnserializableObj>"}
    valid_capture_record_dict["lossy"] = False
    with pytest.raises(ContractError, match="lossy: must be True when repr_fallback tag is present"):
        CaptureRecord.from_dict(valid_capture_record_dict)


def test_test_strength_score_threshold_enforcement(valid_test_strength_dict):
    # Score < 0.70 with insufficient=False must fail
    valid_test_strength_dict["mutants_total"] = 10
    valid_test_strength_dict["mutants_killed"] = 5
    valid_test_strength_dict["score"] = 0.5
    valid_test_strength_dict["insufficient"] = False
    with pytest.raises(ContractError, match="insufficient: must be True when score"):
        TestStrength.from_dict(valid_test_strength_dict)


def test_module_report_fail_closed_verdict(valid_module_report_dict):
    # Verdict SAFE with error/timeout flag must fail
    valid_module_report_dict["verdict"] = "SAFE"
    valid_module_report_dict["flags"] = ["timeout_occurred"]
    with pytest.raises(ContractError, match="verdict: cannot be SAFE when flag"):
        ModuleReport.from_dict(valid_module_report_dict)


def test_snapshot_secret_leakage_prevention():
    # Secret directories
    assert should_exclude("secrets/api_key.json") is True
    assert should_exclude(".ssh/id_rsa") is True
    assert should_exclude("Credentials/db.conf") is True  # Case-insensitive

    # Extensionless SSH keys and token files
    assert should_exclude("id_rsa") is True
    assert should_exclude("id_ed25519") is True
    assert should_exclude("AWS_CREDENTIALS") is True

    # Bulk eval raw results
    assert should_exclude("eval/results/raw_bulk_data.json") is True
