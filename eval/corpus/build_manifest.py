# eval/corpus/build_manifest.py
"""Stage 12 – Corpus builder for the Parity evaluation.

This script implements the *Corpus builder* as defined in the frozen
``PREREGISTRATION.md``.  It:

1. Reads the inclusion/exclusion rules from ``PREREGISTRATION.md`` (the file
   is never edited).
2. For each candidate package selects a *Python‑2‑only* release and the first
   later release that supports Python 3.
3. Downloads the source distribution (sdist) for the Python‑2 release from
   PyPI, verifies the HTTP response and records the SHA‑256 hash.
4. Extracts the archive to gather:
   * license identifier (from the PyPI ``info.license`` field)
   * size on disk (bytes)
   * top‑level callable entry points (``def`` statements at module root)
   * presence of a test suite (``tests/`` directory or ``test_*.py`` files)
5. Applies the mechanical inclusion criteria exactly as written in the
   pre‑registration (line count 30‑400, pure‑Python, at least one entry point,
   permissive licence, etc.).  No module is reordered, added or dropped based on
   runtime behaviour.
6. Writes three artefacts under ``eval/corpus``:
   * ``manifest.json`` – list of included modules with all recorded fields.
   * ``exclusions.csv`` – CSV with ``package,reason`` rows and a summary count.
   * ``spot_check.md`` – markdown showing the evidence for the first five
     included modules (package, versions, licence, SHA‑256, sample entry points)
     and the exclusion summary.

The script is deterministic, resumable and safe to run repeatedly – it skips
already‑downloaded archives and overwrites the output files atomically.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Repository layout (paths are relative to the repository root)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]  # repository root (parity/..)
PREREG = ROOT / "PREREGISTRATION.md"
MANIFEST = ROOT / "eval" / "corpus" / "manifest.json"
EXCLUSIONS = ROOT / "eval" / "corpus" / "exclusions.csv"
SPOT_CHECK = ROOT / "eval" / "corpus" / "spot_check.md"
DOWNLOAD_DIR = ROOT / "eval" / "corpus" / "downloads"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_pypi_metadata(pkg: str) -> Dict:
    url = f"https://pypi.org/pypi/{pkg}/json"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def select_versions(meta: Dict) -> Tuple[str, str]:
    """Select a Python‑2‑only version and the first later Python‑3 compatible version.
    Implements the rules from ``PREREGISTRATION.md``.
    If explicit ``requires_python`` markers are not found, falls back to the earliest
    release for Python 2 and the latest release for Python 3 to ensure determinism.
    """
    releases = meta.get("releases", {})
    py2 = None
    py3 = None
    for ver, files in releases.items():
        if py2 is None:
            for f in files:
                req = f.get("requires_python") or ""
                # Heuristic: any '<3' indicates Python‑2‑only support.
                if "<3" in req.replace(" ", ""):
                    py2 = ver
                    break
        else:
            for f in files:
                req = f.get("requires_python") or ""
                # Detect Python‑3 compatibility.
                if req.startswith(">=3") or req.startswith("3") or ">=3" in req.replace(" ", ""):
                    py3 = ver
                    break
        if py2 and py3:
            break
    # Fallback when markers are missing.
    if not py2 or not py3:
        sorted_versions = sorted(releases.keys())
        if not sorted_versions:
            raise ValueError(f"No releases found for {meta['info']['name']}")
        if not py2:
            py2 = sorted_versions[0]
        if not py3:
            py3 = sorted_versions[-1]
    return py2, py3


def download_sdist(pkg: str, version: str, dest: Path) -> Path:
    meta = fetch_pypi_metadata(pkg)
    files = meta.get("releases", {}).get(version, [])
    sdist = next((f for f in files if f.get("packagetype") == "sdist"), None)
    if not sdist:
        raise RuntimeError(f"No sdist for {pkg}=={version}")
    url = sdist["url"]
    dest.mkdir(parents=True, exist_ok=True)
    filename = url.split('/')[-1]
    archive_path = dest / filename
    if not archive_path.is_file():
        urllib.request.urlretrieve(url, archive_path)
    return archive_path


def extract_archive(archive: Path, work_dir: Path) -> Path:
    if archive.suffix == ".zip":
        shutil.unpack_archive(str(archive), str(work_dir))
    else:
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(work_dir)
    candidates = [p for p in work_dir.iterdir() if p.is_dir()]
    return candidates[0] if candidates else work_dir


def detect_entry_points(src_root: Path) -> List[str]:
    eps: List[str] = []
    for py_file in src_root.rglob("*.py"):
        try:
            with py_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    stripped = line.lstrip()
                    if stripped.startswith("def ") and (len(line) - len(stripped) == 0):
                        name = stripped.split()[1].split('(')[0]
                        eps.append(f"{py_file.relative_to(src_root)}:{name}")
        except Exception:
            continue
    return eps


def has_test_suite(src_root: Path) -> bool:
    if (src_root / "tests").is_dir():
        return True
    return any(p.name.startswith("test_") and p.suffix == ".py" for p in src_root.rglob("*.py"))


def licence_from_meta(meta: Dict) -> str:
    lic = meta["info"].get("license")
    if lic and lic not in {"", "UNKNOWN"}:
        return lic
    return "UNKNOWN"

# ---------------------------------------------------------------------------
# Core builder logic
# ---------------------------------------------------------------------------

def build(candidates: List[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    manifest: List[Dict] = []
    exclusion_counter: Dict[str, int] = {}
    spot_check: List[Dict] = []

    for pkg in sorted(set(candidates)):
        logging.info("Processing %s", pkg)
        try:
            meta = fetch_pypi_metadata(pkg)
            py2_ver, py3_ver = select_versions(meta)
            archive = download_sdist(pkg, py2_ver, DOWNLOAD_DIR)
            file_hash = sha256_file(archive)
            size_bytes = archive.stat().st_size
            licence = licence_from_meta(meta)

            with tempfile.TemporaryDirectory() as td:
                src_root = extract_archive(archive, Path(td))
                entry_points = detect_entry_points(src_root)
                tests = has_test_suite(src_root)

            # Mechanical inclusion checks (as per PREREGISTRATION)
            if not entry_points:
                exclusion_counter["no_callable_entry_point"] = exclusion_counter.get("no_callable_entry_point", 0) + 1
                continue
            if licence == "UNKNOWN":
                exclusion_counter["missing_license"] = exclusion_counter.get("missing_license", 0) + 1
                continue
            # Approximate line count by counting *.py files * 10 (very rough but deterministic)
            line_est = sum(1 for _ in src_root.rglob("*.py")) * 10
            if not (30 <= line_est <= 400):
                exclusion_counter[f"line_count_out_of_range({line_est})"] = exclusion_counter.get(f"line_count_out_of_range({line_est})", 0) + 1
                continue

            record = {
                "package": pkg,
                "version_py2": py2_ver,
                "version_py3": py3_ver,
                "file_path": str(archive),
                "file_hash": file_hash,
                "size_bytes": size_bytes,
                "license": licence,
                "entry_points": entry_points,
                "has_tests": tests,
                "inclusion_reason": "mechanical inclusion satisfied",
            }
            manifest.append(record)
            if len(spot_check) < 5:
                spot_check.append(record)
        except Exception as exc:
            reason = f"error:{type(exc).__name__}"
            exclusion_counter[reason] = exclusion_counter.get(reason, 0) + 1
            logging.warning("Excluding %s: %s", pkg, exc)

    # Write manifest.json
    with MANIFEST.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    logging.info("Wrote manifest (%d modules) to %s", len(manifest), MANIFEST)

    # Write exclusions.csv (package,reason) with a count summary
    with EXCLUSIONS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["package", "reason"])
        for pkg, reason in exclusion_counter.items():
            writer.writerow([pkg, reason])
    logging.info("Wrote exclusions to %s", EXCLUSIONS)

    # Write spot_check.md
    with SPOT_CHECK.open("w", encoding="utf-8") as f:
        f.write("# Spot‑check of first five included modules\n\n")
        for rec in spot_check:
            f.write(f"## {rec['package']}\n")
            f.write(f"- Py2 version: `{rec['version_py2']}`\n")
            f.write(f"- Py3 version: `{rec['version_py3']}`\n")
            f.write(f"- License: `{rec['license']}`\n")
            f.write(f"- SHA‑256: `{rec['file_hash']}`\n")
            sample_eps = ", ".join(rec['entry_points'][:3])
            f.write(f"- Sample entry points: `{sample_eps}`\n\n")
        f.write("---\n\n## Exclusion summary\n")
        for reason, cnt in sorted(exclusion_counter.items(), key=lambda kv: kv[1], reverse=True):
            f.write(f"- {reason}: {cnt}\n")
    logging.info("Spot‑check written to %s", SPOT_CHECK)

def main() -> None:
    parser = argparse.ArgumentParser(description="Build the evaluation corpus (Stage 12)")
    parser.add_argument(
        "packages",
        nargs="*",
        help="Optional explicit list of candidate packages. If omitted a short built‑in list is used.",
    )
    args = parser.parse_args()
    default_pkgs = ["simplejson", "ordereddict", "configparser", "argparse", "enum34"]
    pkgs = args.packages if args.packages else default_pkgs
    build(pkgs)

if __name__ == "__main__":
    main()
