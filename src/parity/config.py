"""Central configuration for PARITY.

Holds comparator rule parameters, thresholds, timeouts, and model settings.
All defaults match CONTRACTS.md.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class ComparatorConfig:
    """Configuration for comparator rules R1–R6 from CONTRACTS.md.

    R1: str/unicode/str3 text equality (no config; bytes vs text is NEVER equal).
    R2: int vs long equality (no config; always numerically equal).
    R3: float tolerance (default exact; relaxation must be recorded).
    R4: dict/set ordering (no config; compare as sets/maps, flag order-dependent).
    R5: exception class name mapping (py2 → py3).
    R6: timing differences (no config; never count as divergence).
    """
    # R3: float comparison tolerance. 0.0 = exact match (CONTRACTS.md default).
    float_tolerance: float = 0.0
    # If float_tolerance != 0.0, this must be True and the relaxation is recorded.
    float_tolerance_relaxed: bool = False

    # R5: explicit py2 → py3 exception class name mapping.
    # e.g. {"StandardError": "Exception"}
    exception_class_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class PARITYConfig:
    """Top-level PARITY configuration."""

    # --- Comparator ---
    comparator: ComparatorConfig = field(default_factory=ComparatorConfig)

    # --- Thresholds ---
    # Test-strength threshold for SAFE verdict (CONTRACTS.md: initial 0.70).
    test_strength_threshold: float = 0.70

    # --- Timeouts ---
    # Max seconds for a subprocess running migrated code.
    subprocess_timeout_seconds: int = 30
    # Max seconds for a single capture execution.
    capture_timeout_seconds: int = 60

    # --- Model settings ---
    llm_backend: str = "ollama"
    llm_model_name: str = "codellama"
    llm_temperature: float = 0.0

    # --- Input generation ---
    input_generator_seed: int = 42
    input_generator_version: str = "0.1.0"

    # --- Schema ---
    schema_version: str = "1.0"

    # ---- Serialization ----

    def to_dict(self) -> dict:
        return {
            "comparator": {
                "float_tolerance": self.comparator.float_tolerance,
                "float_tolerance_relaxed": self.comparator.float_tolerance_relaxed,
                "exception_class_mapping": self.comparator.exception_class_mapping,
            },
            "test_strength_threshold": self.test_strength_threshold,
            "subprocess_timeout_seconds": self.subprocess_timeout_seconds,
            "capture_timeout_seconds": self.capture_timeout_seconds,
            "llm_backend": self.llm_backend,
            "llm_model_name": self.llm_model_name,
            "llm_temperature": self.llm_temperature,
            "input_generator_seed": self.input_generator_seed,
            "input_generator_version": self.input_generator_version,
            "schema_version": self.schema_version,
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    @classmethod
    def from_dict(cls, data: dict) -> "PARITYConfig":
        comp_data = data.get("comparator", {})
        comparator = ComparatorConfig(
            float_tolerance=comp_data.get("float_tolerance", 0.0),
            float_tolerance_relaxed=comp_data.get("float_tolerance_relaxed", False),
            exception_class_mapping=comp_data.get("exception_class_mapping", {}),
        )
        return cls(
            comparator=comparator,
            test_strength_threshold=data.get("test_strength_threshold", 0.70),
            subprocess_timeout_seconds=data.get("subprocess_timeout_seconds", 30),
            capture_timeout_seconds=data.get("capture_timeout_seconds", 60),
            llm_backend=data.get("llm_backend", "ollama"),
            llm_model_name=data.get("llm_model_name", "codellama"),
            llm_temperature=data.get("llm_temperature", 0.0),
            input_generator_seed=data.get("input_generator_seed", 42),
            input_generator_version=data.get("input_generator_version", "0.1.0"),
            schema_version=data.get("schema_version", "1.0"),
        )

    @classmethod
    def from_json(cls, s: str) -> "PARITYConfig":
        return cls.from_dict(json.loads(s))

    @classmethod
    def load(cls, path: str | Path) -> "PARITYConfig":
        """Load config from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def save(self, path: str | Path) -> None:
        """Save config to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=2))
            f.write("\n")
