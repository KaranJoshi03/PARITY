"""Tests for PARITY central config module."""

import json
import pytest

from parity.config import ComparatorConfig, PARITYConfig


def test_default_config():
    cfg = PARITYConfig()
    assert cfg.comparator.float_tolerance == 0.0
    assert cfg.comparator.float_tolerance_relaxed is False
    assert cfg.comparator.exception_class_mapping == {}
    assert cfg.test_strength_threshold == 0.70
    assert cfg.subprocess_timeout_seconds == 30
    assert cfg.capture_timeout_seconds == 60
    assert cfg.llm_backend == "ollama"
    assert cfg.llm_model_name == "codellama"


def test_save_and_load_config(tmp_path):
    cfg_file = tmp_path / "test_config.json"
    cfg = PARITYConfig()
    cfg.test_strength_threshold = 0.85
    cfg.comparator.float_tolerance = 1e-6
    cfg.comparator.float_tolerance_relaxed = True
    cfg.llm_model_name = "llama3:70b"

    cfg.save(cfg_file)
    assert cfg_file.exists()

    loaded = PARITYConfig.load(cfg_file)
    assert loaded.test_strength_threshold == 0.85
    assert loaded.comparator.float_tolerance == 1e-6
    assert loaded.comparator.float_tolerance_relaxed is True
    assert loaded.llm_model_name == "llama3:70b"


def test_json_roundtrip():
    cfg = PARITYConfig()
    json_str = cfg.to_json()
    cfg2 = PARITYConfig.from_json(json_str)
    assert cfg == cfg2
