"""Snapshot tool: creates a timestamped zip of the PARITY project.

Excludes: __pycache__, *.pyc, venvs, .env, secrets, snapshots/,
          node_modules, *.egg-info, eval/results raw bulk.
Includes a RESTORE.txt note inside the zip.
"""

import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import fnmatch

# Patterns to exclude from snapshots.
# Matched against each path component AND the full relative path (case-insensitive).
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".venv",
    "venv",
    ".env",
    "env",
    "*.egg-info",
    "node_modules",
    ".git",
    # Secret directories
    "secrets",
    ".secrets",
    "credentials",
    ".credentials",
    ".ssh",
    ".aws",
    "keys",
    "private",
    # Secrets file extensions & names
    "*.secret",
    "*.key",
    "*.pem",
    "*.token",
    "*.pfx",
    "*.p12",
    "*.kdbx",
    ".env.*",
    "id_rsa*",
    "id_ed25519*",
    "id_dsa*",
    "id_ecdsa*",
    "aws_credentials",
    "credentials.json",
    "secrets.json",
    "api_key*",
    # Snapshots themselves (avoid infinite nesting)
    "snapshots",
    # Raw bulk eval results (too large; summaries are kept)
    "eval/results/raw*",
    "eval/results_raw*",
    "runs/*/eval/results_raw*",
    "eval/results/*.bulk*",
]


def should_exclude(rel_path: str, exclude_patterns: list[str] | None = None) -> bool:
    """Return True if rel_path matches any exclusion pattern.

    Checks against the full relative path and each individual path component,
    performing case-insensitive matching.
    """
    if exclude_patterns is None:
        exclude_patterns = EXCLUDE_PATTERNS
    rel_path_norm = rel_path.replace("\\", "/").lower()
    parts = [p.lower() for p in Path(rel_path).parts]

    for pattern in exclude_patterns:
        pat_lower = pattern.lower()
        if fnmatch.fnmatch(rel_path_norm, pat_lower):
            return True
        for part in parts:
            if fnmatch.fnmatch(part, pat_lower):
                return True
    return False



def create_snapshot(
    project_root: str | Path,
    output_dir: str | Path | None = None,
) -> str:
    """Create a timestamped zip snapshot of the project.

    Args:
        project_root: Root directory of the PARITY project.
        output_dir: Where to write the zip. Defaults to project_root/snapshots/.

    Returns:
        Absolute path to the created zip file.
    """
    project_root = Path(project_root).resolve()

    if output_dir is None:
        output_dir = project_root / "snapshots"
    else:
        output_dir = Path(output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_name = f"parity_snapshot_{timestamp}.zip"
    zip_path = output_dir / zip_name

    if zip_path.exists():
        raise FileExistsError(f"Snapshot already exists: {zip_path}")

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_root):
            # Prune excluded directories in-place
            dirs[:] = [
                d for d in dirs
                if not should_exclude(
                    os.path.relpath(os.path.join(root, d), project_root),
                )
            ]
            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, project_root)
                if not should_exclude(rel_path):
                    zf.write(full_path, rel_path)
                    file_count += 1

        # Add restore note
        restore_note = (
            f"PARITY Snapshot\n"
            f"Created: {timestamp}\n"
            f"Source:  {project_root}\n"
            f"Files:   {file_count}\n"
            f"\n"
            f"To restore: unzip into the project root directory.\n"
            f"This snapshot excludes:\n"
            f"  - Python caches (__pycache__, *.pyc)\n"
            f"  - Virtual environments (.venv, venv)\n"
            f"  - Secrets (*.secret, *.key, *.pem, *.token)\n"
            f"  - Other snapshots (snapshots/)\n"
            f"  - Raw bulk eval results\n"
            f"  - Node modules, .git\n"
        )
        zf.writestr("RESTORE.txt", restore_note)

    return str(zip_path)


def main() -> None:
    """CLI entry point for parity-snapshot."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a timestamped snapshot of the PARITY project.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for the zip (default: <project-root>/snapshots/)",
    )
    args = parser.parse_args()

    try:
        zip_path = create_snapshot(args.project_root, args.output_dir)
        print(f"Snapshot created: {zip_path}")
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error creating snapshot: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
