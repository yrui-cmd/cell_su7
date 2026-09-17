"""Synchronize the official cell_no_ai skill without touching credentials."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath


REPOSITORY = "https://github.com/yrui-cmd/cell_no_ai"
ARCHIVE_URL = "https://codeload.github.com/yrui-cmd/cell_no_ai/zip/refs/heads/main"


def _git_checkout(checkout):
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", "main", f"{REPOSITORY}.git", str(checkout)],
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    names = subprocess.check_output(
        ["git", "-C", str(checkout), "ls-files"], text=True
    ).splitlines()
    return revision, names


def _archive_checkout(checkout):
    if checkout.exists():
        shutil.rmtree(checkout)
    request = urllib.request.Request(
        ARCHIVE_URL, headers={"User-Agent": "cell_su7-dependency-sync"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    names = []
    archive = zipfile.ZipFile(BytesIO(payload))
    roots = {
        PurePosixPath(item.filename).parts[0]
        for item in archive.infolist()
        if PurePosixPath(item.filename).parts
    }
    if len(roots) != 1:
        raise RuntimeError("Unexpected upstream archive layout")
    root = roots.pop()
    for item in archive.infolist():
        parts = PurePosixPath(item.filename).parts
        if item.is_dir() or len(parts) < 2 or parts[0] != root:
            continue
        relative = Path(*parts[1:])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Unsafe upstream archive path")
        target = checkout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(item))
        names.append(relative.as_posix())
    if not names:
        raise RuntimeError("Empty upstream archive")
    return f"archive-sha256:{digest}", names


def _source_files(names):
    return [
        Path(name)
        for name in names
        if name == "SKILL.md" or Path(name).parts[0] in ("agents", "references", "scripts")
    ]


def sync(destination):
    destination = Path(destination).resolve()
    with tempfile.TemporaryDirectory(prefix="cell-no-ai-update-") as temp:
        checkout = Path(temp) / "source"
        try:
            revision, names = _git_checkout(checkout)
        except (OSError, subprocess.CalledProcessError):
            revision, names = _archive_checkout(checkout)

        files = _source_files(names)
        if not (checkout / "SKILL.md").is_file():
            raise RuntimeError("Missing upstream SKILL.md")
        for relative in files:
            source = checkout / relative
            target = destination / relative
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or source.is_symlink()
                or not target.resolve().is_relative_to(destination)
            ):
                raise RuntimeError("Unsafe skill path")

        destination.mkdir(parents=True, exist_ok=True)
        backup = destination.parent / ".cell_no_ai-backups" / str(time.time_ns())
        changed = 0
        for relative in files:
            source = checkout / relative
            target = destination / relative
            if target.is_file() and target.read_bytes() == source.read_bytes():
                continue
            if target.exists():
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            changed += 1

        (destination / ".upstream.json").write_text(
            json.dumps({"repository": REPOSITORY, "revision": revision}), encoding="utf-8"
        )
        print(f"SYNC_OK|revision={revision}|changed={changed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--destination", default=str(Path(__file__).resolve().parents[2] / "cell_no_ai")
    )
    args = parser.parse_args()
    try:
        sync(args.destination)
    except Exception as exc:
        raise SystemExit(
            "SYNC_FAILED|"
            + type(exc).__name__
            + "|existing_installation_preserved; retry before watermark submission"
        )
