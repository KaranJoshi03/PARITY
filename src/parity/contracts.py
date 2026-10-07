"""PARITY contract data classes — strict, validated, JSON-serializable.

Implements every contract object from CONTRACTS.md:
  - CaptureRecord   (§ CaptureRecord)
  - MigrationResult  (§ MigrationResult)
  - Divergence       (§ Divergence)
  - TestStrength     (§ TestStrength)
  - ModuleReport     (§ ModuleReport)

All objects reject unknown fields, missing required fields, and invalid
values.  Round-trip JSON: from_dict / to_dict / from_json / to_json.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import asdict, dataclass, fields
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants – taken verbatim from CONTRACTS.md
# ---------------------------------------------------------------------------

OUTPUT_KEYS = frozenset({"return", "exception", "stdout", "stderr"})

SIDE_EFFECT_KEYS = frozenset({
    "time", "random", "file_io", "network", "env", "global_state",
})

DIVERGENCE_CATEGORIES = frozenset({
    "value", "type", "exception_type", "exception_message",
    "stdout", "ordering", "encoding", "numeric", "timing",
})

SEVERITY_LEVELS = frozenset({"low", "high"})

VERDICT_VALUES = frozenset({"SAFE", "RISKY", "BLOCKED"})


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ContractError(Exception):
    """Raised when a contract object fails validation."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _check_str(
    value: Any, field_name: str, cls_name: str, *, allow_empty: bool = False,
) -> None:
    if not isinstance(value, str):
        raise ContractError(
            f"{cls_name}.{field_name}: expected str, got {type(value).__name__}"
        )
    if not allow_empty and not value:
        raise ContractError(f"{cls_name}.{field_name}: must be non-empty")


def _check_bool(value: Any, field_name: str, cls_name: str) -> None:
    if not isinstance(value, bool):
        raise ContractError(
            f"{cls_name}.{field_name}: expected bool, got {type(value).__name__}"
        )


def _check_int(value: Any, field_name: str, cls_name: str) -> None:
    # bool is a subclass of int in Python — reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(
            f"{cls_name}.{field_name}: expected int, got {type(value).__name__}"
        )


def _check_number(value: Any, field_name: str, cls_name: str) -> None:
    """Accept int or float (not bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(
            f"{cls_name}.{field_name}: expected number, got {type(value).__name__}"
        )


def _check_dict(value: Any, field_name: str, cls_name: str) -> None:
    if not isinstance(value, dict):
        raise ContractError(
            f"{cls_name}.{field_name}: expected dict, got {type(value).__name__}"
        )


def _check_list(value: Any, field_name: str, cls_name: str) -> None:
    if not isinstance(value, list):
        raise ContractError(
            f"{cls_name}.{field_name}: expected list, got {type(value).__name__}"
        )


def _check_dict_keys(
    value: Any,
    field_name: str,
    cls_name: str,
    expected_keys: frozenset[str],
) -> None:
    _check_dict(value, field_name, cls_name)
    actual = set(value.keys())
    if actual != expected_keys:
        missing = expected_keys - actual
        extra = actual - expected_keys
        parts: list[str] = []
        if missing:
            parts.append(f"missing: {sorted(missing)}")
        if extra:
            parts.append(f"unexpected: {sorted(extra)}")
        raise ContractError(
            f"{cls_name}.{field_name}: key mismatch — {'; '.join(parts)}"
        )


def _check_enum(
    value: Any,
    field_name: str,
    cls_name: str,
    allowed: frozenset[str],
) -> None:
    if value not in allowed:
        raise ContractError(
            f"{cls_name}.{field_name}: '{value}' not in {sorted(allowed)}"
        )


# ---------------------------------------------------------------------------
# Base mixin
# ---------------------------------------------------------------------------

class StrictContract:
    """Mixin providing strict ``from_dict`` / ``to_dict`` for dataclasses.

    Rules:
    - Unknown keys in the input dict are rejected.
    - Missing keys for required fields (those without a default) are rejected.
    - ``__post_init__`` performs value-level validation.
    """

    @classmethod
    def _required_field_names(cls) -> frozenset[str]:
        return frozenset(
            f.name
            for f in fields(cls)  # type: ignore[arg-type]
            if f.default is dataclasses.MISSING
            and f.default_factory is dataclasses.MISSING  # type: ignore[arg-type]
        )

    @classmethod
    def _all_field_names(cls) -> frozenset[str]:
        return frozenset(f.name for f in fields(cls))  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, data: dict) -> "StrictContract":
        """Build from a plain dict.  Rejects unknown and missing fields."""
        name = cls.__name__
        if not isinstance(data, dict):
            raise ContractError(
                f"{name}: expected dict, got {type(data).__name__}"
            )

        all_names = cls._all_field_names()
        required = cls._required_field_names()

        unknown = set(data.keys()) - all_names
        if unknown:
            raise ContractError(f"{name}: unknown fields: {sorted(unknown)}")

        missing = required - set(data.keys())
        if missing:
            raise ContractError(
                f"{name}: missing required fields: {sorted(missing)}"
            )

        filtered = {k: v for k, v in data.items() if k in all_names}
        return cls(**filtered)  # type: ignore[call-arg]

    def to_dict(self) -> dict:
        """Serialize to a plain dict (recursively converts nested dataclasses)."""
        return asdict(self)  # type: ignore[call-overload]

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    @classmethod
    def from_json(cls, s: str) -> "StrictContract":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# Contract objects
# ---------------------------------------------------------------------------

@dataclass(frozen=False)
class CaptureRecord(StrictContract):
    """One execution of an entry point under py2 — CONTRACTS.md § CaptureRecord.

    All fields are required (key must be present in the dict).
    ``non_determinism_reason`` may be ``None``.
    """

    module: str
    entry_point: str
    input: dict                        # serialized args/kwargs, type-tagged
    outputs: dict                      # {return, exception, stdout, stderr}
    duration_ms: float
    runs: int
    deterministic: bool
    non_determinism_reason: Optional[str]
    side_effect_flags: dict            # {time, random, file_io, network, env, global_state}
    lossy: bool

    def __post_init__(self) -> None:
        n = "CaptureRecord"
        _check_str(self.module, "module", n)
        _check_str(self.entry_point, "entry_point", n)
        _check_dict(self.input, "input", n)

        # outputs must have exactly the four prescribed keys
        _check_dict_keys(self.outputs, "outputs", n, OUTPUT_KEYS)
        _check_str(self.outputs["stdout"], "outputs.stdout", n, allow_empty=True)
        _check_str(self.outputs["stderr"], "outputs.stderr", n, allow_empty=True)

        _check_number(self.duration_ms, "duration_ms", n)
        if self.duration_ms < 0:
            raise ContractError(f"{n}.duration_ms: must be >= 0")

        _check_int(self.runs, "runs", n)
        if self.runs < 1:
            raise ContractError(f"{n}.runs: must be >= 1")

        _check_bool(self.deterministic, "deterministic", n)

        if not self.deterministic:
            if not self.non_determinism_reason:
                raise ContractError(
                    f"{n}.non_determinism_reason: required when deterministic is False"
                )
            _check_str(self.non_determinism_reason, "non_determinism_reason", n)
        else:
            if self.non_determinism_reason is not None:
                raise ContractError(
                    f"{n}.non_determinism_reason: must be None when deterministic is True"
                )

        # side_effect_flags: exactly the six prescribed keys, all bool
        _check_dict_keys(
            self.side_effect_flags, "side_effect_flags", n, SIDE_EFFECT_KEYS,
        )
        for k, v in self.side_effect_flags.items():
            if not isinstance(v, bool):
                raise ContractError(
                    f"{n}.side_effect_flags.{k}: expected bool, "
                    f"got {type(v).__name__}"
                )

        _check_bool(self.lossy, "lossy", n)
        # CONTRACTS.md § Serialization: Anything tagged repr_fallback must be flagged lossy
        input_outputs_str = json.dumps(self.input) + json.dumps(self.outputs)
        if '"repr_fallback"' in input_outputs_str and not self.lossy:
            raise ContractError(f"{n}.lossy: must be True when repr_fallback tag is present")


@dataclass(frozen=False)
class MigrationResult(StrictContract):
    """Result of one LLM migration attempt — CONTRACTS.md § MigrationResult.

    All fields required.  ``parsed_code`` and ``parse_error`` may be ``None``.
    """

    module: str
    backend: str
    model_name: str
    parameters: dict
    prompt: str
    raw_output: str
    parsed_code: Optional[str]
    parse_ok: bool
    parse_error: Optional[str]
    timestamp: str
    duration_ms: float

    def __post_init__(self) -> None:
        n = "MigrationResult"
        _check_str(self.module, "module", n)
        _check_str(self.backend, "backend", n)
        _check_str(self.model_name, "model_name", n)
        _check_dict(self.parameters, "parameters", n)
        _check_str(self.prompt, "prompt", n)
        _check_str(self.raw_output, "raw_output", n, allow_empty=True)

        if self.parsed_code is not None:
            _check_str(self.parsed_code, "parsed_code", n, allow_empty=True)

        _check_bool(self.parse_ok, "parse_ok", n)

        if self.parse_error is not None:
            _check_str(self.parse_error, "parse_error", n, allow_empty=True)

        _check_str(self.timestamp, "timestamp", n)
        _check_number(self.duration_ms, "duration_ms", n)
        if self.duration_ms < 0:
            raise ContractError(f"{n}.duration_ms: must be >= 0")


@dataclass(frozen=False)
class Divergence(StrictContract):
    """A single behavioral divergence — CONTRACTS.md § Divergence.

    All fields required.  ``comparator_rule_applied`` may be ``None``.
    """

    module: str
    entry_point: str
    input: dict
    py2_behavior: dict
    py3_behavior: dict
    category: str       # value|type|exception_type|exception_message|stdout|ordering|encoding|numeric|timing
    comparator_rule_applied: Optional[str]
    severity: str       # low|high

    def __post_init__(self) -> None:
        n = "Divergence"
        _check_str(self.module, "module", n)
        _check_str(self.entry_point, "entry_point", n)
        _check_dict(self.input, "input", n)
        _check_dict(self.py2_behavior, "py2_behavior", n)
        _check_dict(self.py3_behavior, "py3_behavior", n)
        _check_enum(self.category, "category", n, DIVERGENCE_CATEGORIES)

        if self.comparator_rule_applied is not None:
            _check_str(
                self.comparator_rule_applied, "comparator_rule_applied", n,
            )

        _check_enum(self.severity, "severity", n, SEVERITY_LEVELS)


@dataclass(frozen=False)
class TestStrength(StrictContract):
    """Mutation-testing strength measurement — CONTRACTS.md § TestStrength.

    ``score`` must equal ``mutants_killed / mutants_total`` (or 0.0 when
    ``mutants_total == 0``).
    """

    __test__ = False

    mutants_total: int
    mutants_killed: int
    score: float
    mutation_operators_used: list
    survivors: list
    insufficient: bool

    def __post_init__(self) -> None:
        n = "TestStrength"
        _check_int(self.mutants_total, "mutants_total", n)
        _check_int(self.mutants_killed, "mutants_killed", n)
        _check_number(self.score, "score", n)
        _check_list(self.mutation_operators_used, "mutation_operators_used", n)
        _check_list(self.survivors, "survivors", n)
        _check_bool(self.insufficient, "insufficient", n)

        if self.mutants_total < 0:
            raise ContractError(f"{n}.mutants_total: must be >= 0")
        if self.mutants_killed < 0:
            raise ContractError(f"{n}.mutants_killed: must be >= 0")
        if self.mutants_killed > self.mutants_total:
            raise ContractError(
                f"{n}.mutants_killed ({self.mutants_killed}) > "
                f"mutants_total ({self.mutants_total})"
            )

        # Validate score = killed/total (CONTRACTS.md: "score = killed/total")
        if self.mutants_total == 0:
            expected = 0.0
        else:
            expected = self.mutants_killed / self.mutants_total
        if abs(self.score - expected) > 1e-9:
            raise ContractError(
                f"{n}.score: {self.score} != killed/total ({expected})"
            )

        # CONTRACTS.md § Verdict: test strength below initial 0.70 threshold must be marked insufficient
        if self.score < 0.70 and not self.insufficient:
            raise ContractError(
                f"{n}.insufficient: must be True when score ({self.score}) < 0.70 threshold"
            )


@dataclass(frozen=False)
class ModuleReport(StrictContract):
    """Per-module verdict report — CONTRACTS.md § ModuleReport.

    All fields required.  ``human_migration_comparison`` may be ``None``.
    """

    module: str
    verdict: str                           # SAFE | RISKY | BLOCKED
    evidence: list                         # links to captured records / divergences
    test_strength: dict                    # TestStrength-shaped dict
    flags: list
    human_migration_comparison: Optional[dict]
    timings: dict

    def __post_init__(self) -> None:
        n = "ModuleReport"
        _check_str(self.module, "module", n)
        _check_enum(self.verdict, "verdict", n, VERDICT_VALUES)
        _check_list(self.evidence, "evidence", n)
        _check_dict(self.test_strength, "test_strength", n)
        _check_list(self.flags, "flags", n)

        if self.human_migration_comparison is not None:
            _check_dict(
                self.human_migration_comparison,
                "human_migration_comparison",
                n,
            )

        _check_dict(self.timings, "timings", n)

        # Fail-closed verdict checks (CONTRACTS.md § Verdict)
        if self.verdict == "SAFE":
            unsafe_flag_keywords = {
                "timeout", "error", "unparsed", "non_determinism",
                "lossy", "insufficient", "unsupported", "divergence",
            }
            for flag in self.flags:
                if any(kw in flag.lower() for kw in unsafe_flag_keywords):
                    raise ContractError(
                        f"{n}.verdict: cannot be SAFE when flag '{flag}' is present"
                    )

            if self.test_strength.get("insufficient") is True or self.test_strength.get("score", 1.0) < 0.70:
                raise ContractError(
                    f"{n}.verdict: cannot be SAFE when test_strength is insufficient"
                )


        _check_dict(self.timings, "timings", n)
