#!/usr/bin/env python3
"""Image-to-editable-PPTX wrapper with optional live text restoration."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(*args: str):
    subprocess.run([sys.executable, *args], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application", choices=["ppt", "ai"], default="ppt")
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--text-manifest", type=Path, help="Recorded original text; input image must already be text-free")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--input-pptx", type=Path)
    parser.add_argument("--slide-index", type=int, default=0)
    parser.add_argument("--estimated-credits", type=int, default=1)
    parser.add_argument("--approve-high-cost", action="store_true")
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    allocator = scripts / "allocate_shibielujing_name.py"
    base_name = subprocess.check_output(
        [sys.executable, str(allocator), "--root", str(args.output_root.resolve())], text=True
    ).strip().splitlines()[-1]
    job = args.output_root.resolve() / base_name
    job.mkdir(parents=True, exist_ok=True)
    if args.text_manifest:
        recorded_manifest = job / "text-manifest.json"
        shutil.copyfile(args.text_manifest.resolve(), recorded_manifest)
        args.text_manifest = recorded_manifest

    raw_svg = job / f"{base_name}-vector.svg"
    master_svg = job / f"{base_name}.svg"
    vector_command = [
        str(scripts / "vectorize_xiaomiao.py"),
        "--input-image", str(args.input_image.resolve()),
        "--output-svg", str(raw_svg),
        "--estimated-credits", str(args.estimated_credits),
    ]
    if args.approve_high_cost:
        vector_command.append("--approve-high-cost")
    run(*vector_command)
    if args.text_manifest:
        run(str(scripts / "merge_live_text.py"), "--input-svg", str(raw_svg),
            "--text-manifest", str(args.text_manifest.resolve()), "--output-svg", str(master_svg))
    else:
        shutil.copyfile(raw_svg, master_svg)
    command = [str(scripts / ("run_from_svg.py" if args.application == "ppt" else "run_illustrator.py")),
               "--input-svg", str(master_svg), "--output-root", str(args.output_root.resolve()), "--job-name", base_name]
    if args.application == "ppt":
        command.extend(["--slide-index", str(args.slide_index)])
        if args.input_pptx:
            command.extend(["--input-pptx", str(args.input_pptx.resolve())])
    elif args.input_pptx:
        raise ValueError("--input-pptx only applies to PowerPoint")
    run(*command)
    print(json.dumps({"ok": True, "base_name": base_name, "master_svg": str(master_svg)}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
