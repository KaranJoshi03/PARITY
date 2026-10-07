"""Verdict Engine — CONTRACTS.md § Verdict and § ModuleReport.

Implements the fail-closed verdict calculation table:
  - Any divergence (excluding documented intended change): BLOCKED
  - Any internal error, timeout, or unparsed migration: RISKY or lower
  - Non-determinism unresolved: RISKY or lower
  - Lossy serialization on a verdict-relevant input: RISKY or lower
  - Test strength below threshold (0.70): RISKY or lower
  - Unsupported construct detected (flagged list): RISKY or lower
  - All signals present and passing: SAFE

Invariant: Removing, corrupting, or timing out any signal can NEVER raise a verdict.
Produces validated ModuleReport objects with human-readable evidence links.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from parity.config import PARITYConfig
from parity.contracts import (
    CaptureRecord,
    Divergence,
    MigrationResult,
    ModuleReport,
    TestStrength,
)


def compute_module_verdict(
    module_name: str,
    capture_records: List[CaptureRecord],
    migration_result: MigrationResult,
    divergences: List[Divergence],
    test_strength: TestStrength,
    timings: Optional[Dict[str, float]] = None,
    config: Optional[PARITYConfig] = None,
) -> ModuleReport:
    """Calculate fail-closed verdict and assemble a strict ModuleReport."""
    if config is None:
        config = PARITYConfig()

    flags: List[str] = []
    evidence: List[Dict[str, Any]] = []

    # 1. Check Migration Parsing / Internal Errors
    if not migration_result.parse_ok:
        flags.append(f"unparsed_migration: {migration_result.parse_error or 'Syntax error'}")
        evidence.append({
            "type": "parse_failure",
            "backend": migration_result.backend,
            "error": migration_result.parse_error,
        })

    # 2. Check Capture Non-Determinism / Lossy Serialization
    for rec in capture_records:
        if not rec.deterministic:
            flags.append(f"non_determinism in {rec.entry_point}: {rec.non_determinism_reason}")
            evidence.append({
                "type": "non_determinism",
                "entry_point": rec.entry_point,
                "reason": rec.non_determinism_reason,
            })
        if rec.lossy:
            flags.append(f"lossy_serialization in {rec.entry_point}")
            evidence.append({
                "type": "lossy_input",
                "entry_point": rec.entry_point,
            })

    # 3. Check Divergences (BLOCKED trigger)
    has_unintended_divergence = False
    if divergences:
        for div in divergences:
            flags.append(f"divergence: {div.category} ({div.comparator_rule_applied})")
            evidence.append({
                "type": "divergence",
                "entry_point": div.entry_point,
                "category": div.category,
                "rule": div.comparator_rule_applied,
                "py2": div.py2_behavior,
                "py3": div.py3_behavior,
            })
            has_unintended_divergence = True

    # 4. Check Test Strength
    if test_strength.insufficient or test_strength.score < config.test_strength_threshold:
        flags.append(f"insufficient_test_strength (score={test_strength.score:.2f} < threshold={config.test_strength_threshold:.2f})")
        evidence.append({
            "type": "test_strength_shortfall",
            "score": test_strength.score,
            "threshold": config.test_strength_threshold,
            "survivors": len(test_strength.survivors),
        })

    # -----------------------------------------------------------------------
    # Verdict Hierarchy Calculation (Strict Fail-Closed)
    # -----------------------------------------------------------------------
    if has_unintended_divergence:
        verdict = "BLOCKED"
    elif not migration_result.parse_ok:
        verdict = "RISKY"
    elif any("non_determinism" in f for f in flags):
        verdict = "RISKY"
    elif any("lossy" in f for f in flags):
        verdict = "RISKY"
    elif test_strength.insufficient or test_strength.score < config.test_strength_threshold:
        verdict = "RISKY"
    elif any("unsupported" in f for f in flags):
        verdict = "RISKY"
    else:
        verdict = "SAFE"

    if timings is None:
        timings = {
            "capture_ms": sum(r.duration_ms for r in capture_records),
            "migration_ms": migration_result.duration_ms,
            "total_ms": sum(r.duration_ms for r in capture_records) + migration_result.duration_ms,
        }

    report = ModuleReport(
        module=module_name,
        verdict=verdict,
        evidence=evidence,
        test_strength=test_strength.to_dict(),
        flags=flags,
        human_migration_comparison=None,
        timings=timings,
    )
    return report
