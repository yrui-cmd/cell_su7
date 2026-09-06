#!/usr/bin/env python3
"""Cross-platform cell_su7 skill installer."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path.home() / ".codex" / "skills")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project = Path(__file__).resolve().parent
    source = project / "plugins" / "cell_su7" / "skills" / "cell_su7"
    target_root = args.destination.expanduser().resolve()
    target = target_root / "cell_su7"
    if not source.is_dir():
        raise SystemExit(f"Plugin skill directory is missing: {source}")
    dependency_source = source.parent / "cell_no_ai"
    dependency_target = target_root / "cell_no_ai"
    if not (dependency_source / "SKILL.md").is_file():
        raise SystemExit("Required bundled dependency cell_no_ai is missing.")
    if dependency_target.exists() and not (dependency_target / "SKILL.md").is_file():
        raise SystemExit(f"Existing dependency is incomplete: {dependency_target}; repair it before installation.")
    target_root.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not args.force:
            raise SystemExit(f"Skill already exists: {target}. Re-run with --force only if replacement is intended.")
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    # Preserve an independently installed dependency, including junction installs.
    if not dependency_target.exists():
        shutil.copytree(dependency_source, dependency_target,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        print(f"INSTALLED|skill=cell_no_ai|destination={dependency_target}|dependency=cell_su7")
    else:
        print(f"PRESERVED|skill=cell_no_ai|destination={dependency_target}|dependency=cell_su7")
    subprocess.run(
        [sys.executable, str(target / "scripts" / "configure_runtime.py"), "--output", str(target / "runtime-profile.json")],
        check=True,
    )
    print(f"INSTALLED|skill=cell_su7|destination={target}|copy=true")
    print("Restart Codex and start a new task before first use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
