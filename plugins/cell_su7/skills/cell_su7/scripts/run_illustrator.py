#!/usr/bin/env python3
"""Illustrator native batch drawing: Windows COM or macOS AppleScript/JSX."""
import argparse
import json
import platform
import subprocess
import sys
import time
from urllib.parse import unquote
from pathlib import Path
import prepare_illustrator_cache as builder

BUNDLE = 'com.adobe.illustrator'

def apple_string(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n') + '"'

def invoke_mac(script, work):
    # Compile against the installed Illustrator dictionary. Existing app only.
    path = work / 'current-call.jsx'
    path.write_text(script, encoding='utf-8')
    apple = ('if not (application id "' + BUNDLE + '" is running) then error "AI_DOCUMENT_REQUIRED: Open Illustrator first"\n'
             'tell application id "' + BUNDLE + '"\n'
             'with timeout of 600 seconds\n'
             'do javascript (POSIX file ' + apple_string(path) + ' as alias)\n'
             'end timeout\nend tell')
    proc = subprocess.run(['osascript', '-e', apple], capture_output=True, text=True, timeout=630)
    if proc.returncode:
        raise RuntimeError('Illustrator AppleScript failed (check macOS Automation permission): ' + proc.stderr.strip())
    result = proc.stdout.strip()
    if result.startswith(('ERROR', 'PARTIAL')):
        raise RuntimeError(result)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-svg', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    parser.add_argument('--job-name', default='shibielujing1')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if Path(args.job_name).name != args.job_name or args.job_name in {'.','..'}:
        parser.error('job-name must be a single directory name')
    scripts = Path(__file__).resolve().parent
    job = args.output_root.resolve() / args.job_name
    job.mkdir(parents=True, exist_ok=True)
    work = job / '.illustrator-cache'
    if platform.system() == 'Windows' and not args.dry_run:
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(scripts / 'run_cell_lct.ps1'),
                        '-InputSvg', str(args.input_svg.resolve()), '-WorkDir', str(work),
                        '-OutputAi', str(job / (args.job_name + '.ai')), '-OutputPng', str(job / (args.job_name + '.png'))], check=True)
        return 0
    cache, state = builder.prepare(args.input_svg, work, args.job_name, 20, 50, 320, 2200)
    if args.dry_run:
        print(json.dumps({'ok':True,'mode':'dry-run','atoms':len(cache['atoms']),'batches':len(cache['batches']), 'desktop_tested':False}))
        return 0
    if platform.system() != 'Darwin':
        raise RuntimeError('Illustrator host requires Windows or macOS')
    state_path = work / 'playback.json'
    fields = invoke_mac('(function(){if(!app.documents.length)return "ERROR|AI_DOCUMENT_REQUIRED";var d=app.activeDocument;return encodeURIComponent(d.name)+"|"+encodeURIComponent(d.activeLayer.name);}())', work).split('|')
    if len(fields) != 2:
        raise RuntimeError('Invalid Illustrator document response')
    info = dict(name=unquote(fields[0]),layer=unquote(fields[1]))
    if state.get('target_document') and (state['target_document'] != info['name'] or state.get('target_layer') != info['layer']):
        raise RuntimeError('Resume requires the same active Illustrator document and layer')
    state.update(target_document=info['name'], target_layer=info['layer'])
    builder.write_json_atomic(state_path, state)
    runtime = (scripts / 'cell_lct_cached_runtime.jsx').read_text(encoding='utf-8-sig')
    def call(config):
        result = invoke_mac('var CELL_LCT_CACHED_CONFIG=' + json.dumps(config, ensure_ascii=True) + ';\n' + runtime, work)
        if not result.startswith('OK|'):
            raise RuntimeError('Unexpected Illustrator response: ' + result[:300])
        return result
    last_save = time.monotonic()
    def save():
        result = call(dict(operation='save',targetDocumentName=state['target_document'],outputAi=str(job/(args.job_name+'.ai'))))
        if '|documentName=' in result:
            state['target_document'] = result.split('|documentName=',1)[1]
            builder.write_json_atomic(state_path,state)
    for batch in state['batches']:
        # Reconcile actual named objects on resume: the runtime skips existing
        # atoms, but rebuilds objects lost since the last native save.
        payload = work / 'current-batch.json'
        builder.write_json_atomic(payload, {'viewBox':cache['view_box'], 'atoms':[cache['atoms'][i] for i in batch['atom_indices']]})
        config = dict(operation='draw',batchJsonPath=str(payload),targetDocumentName=state['target_document'],
                      targetLayerName=state['target_layer'],rootGroupName=state['root_group_name'],batchGroupName=batch['group_name'],
                      placement='center',maxWidthFraction=.72,maxHeightFraction=.78,delayMs=0)
        call(config)
        batch['completed'] = True
        builder.write_json_atomic(state_path, state)
        print(f"DRAW|batch={batch['index']+1}/{len(state['batches'])}",flush=True)
        if time.monotonic()-last_save >= 60:
            save()
            last_save=time.monotonic()
    call(dict(operation='normalize',targetDocumentName=state['target_document'],targetLayerName=state['target_layer'],rootGroupName=state['root_group_name'],batchGroupNames=[b['group_name'] for b in state['batches']]))
    save()
    call(dict(operation='export',targetDocumentName=state['target_document'],outputPng=str(job/(args.job_name+'.png'))))
    if not all((job/(args.job_name+suffix)).is_file() for suffix in ('.ai','.png')):
        raise RuntimeError('Illustrator did not create the requested AI and PNG files')
    print(json.dumps({'ok':True,'ai':str(job/(args.job_name+'.ai')),'png':str(job/(args.job_name+'.png'))}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
