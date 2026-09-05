"""Keep back-to-front source order, including repeated background layers."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/cell_su7/skills/cell_su7/scripts'

def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, capture_output=True)

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    background = 'd="M0 0L100 0L100 100L0 100Z" fill="white"'
    parts = [f'<path id="base-first" {background}/>', f'<path id="base-adjacent" {background}/>']
    for index in range(55):
        parts.append(f'<path id="detail-{index}" d="M{index} 5h1v1h-1Z" fill="red"/>')
    parts.append(f'<path id="base-later" {background}/>')
    for index in range(2):
        parts.append(f'<path id="translucent-{index}" d="M10 10h40v40h-40Z" fill="blue" opacity="0.5"/>')
    svg = work / 'input.svg'
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' + ''.join(parts) + '</svg>', encoding='utf-8')
    for backend, builder in [('ppt', 'prepare_geometry_cache.py'), ('ai', 'prepare_illustrator_cache.py')]:
        output = work / backend
        run(SCRIPTS / builder, '--input', svg, '--output-dir', output, '--job-id', 'order')
        if backend == 'ppt':
            run(SCRIPTS / 'cull_hidden_geometry.py', '--cache', output / 'geometry-cache.json', '--state', output / 'drawing-state.json')
        cache = json.loads((output / 'geometry-cache.json').read_text(encoding='utf-8'))
        sequence = [i for batch in cache['batches'] for i in batch['atom_indices']]
        assert sequence == list(range(len(cache['atoms']))), 'Batches reordered source atoms'
        ids = [cache['atoms'][i]['sourceId'] for i in sequence]
        assert ids[0] == 'base-first', ids
        assert ids.index('base-later') > ids.index('detail-54')
        assert ids[-2:] == ['translucent-0', 'translucent-1']
        if backend == 'ppt':
            assert 'base-adjacent' not in ids
            assert cache['culled_atom_count'] == 1
print('PAINT_ORDER_OK|base=first|cross-layer-duplicates=preserved|transparency=preserved|batch-order=ppt,ai')
