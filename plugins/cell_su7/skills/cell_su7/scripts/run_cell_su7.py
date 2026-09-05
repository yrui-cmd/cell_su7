#!/usr/bin/env python3
"""Cross-platform selector for prepared images or approved SVGs."""
import argparse
from pathlib import Path
import platform
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser()
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input-image',type=Path)
    source.add_argument('--input-svg',type=Path)
    parser.add_argument('--text-manifest',type=Path)
    parser.add_argument('--output-root',required=True,type=Path)
    parser.add_argument('--application',required=True,choices=['ppt','ai'])
    parser.add_argument('--estimated-credits',type=int,default=1)
    parser.add_argument('--approve-high-cost',action='store_true')
    args=parser.parse_args()
    scripts=Path(__file__).resolve().parent
    if args.input_svg:
        if args.text_manifest:
            parser.error('Merge the text manifest into the approved SVG before using --input-svg')
        name=subprocess.check_output([sys.executable,str(scripts/'allocate_shibielujing_name.py'),'--root',str(args.output_root)],text=True).strip()
        command=[sys.executable,str(scripts/('run_from_svg.py' if args.application=='ppt' else 'run_illustrator.py')),
                 '--input-svg',str(args.input_svg),'--output-root',str(args.output_root),'--job-name',name]
    elif platform.system()=='Windows':
        command=['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(scripts/'run_cell_su7.ps1'),
                 '-InputImage',str(args.input_image),'-OutputRoot',str(args.output_root),'-Application',args.application,'-EstimatedCredits',str(args.estimated_credits)]
        if args.text_manifest: command+=['-TextManifest',str(args.text_manifest)]
        if args.approve_high_cost: command+=['-ApproveHighCost']
    else:
        command=[sys.executable,str(scripts/'run_from_image.py'),'--input-image',str(args.input_image),
                 '--output-root',str(args.output_root),'--application',args.application,'--estimated-credits',str(args.estimated_credits)]
        if args.text_manifest: command+=['--text-manifest',str(args.text_manifest)]
        if args.approve_high_cost: command+=['--approve-high-cost']
    subprocess.run(command,check=True)
    return 0

if __name__=='__main__': raise SystemExit(main())
