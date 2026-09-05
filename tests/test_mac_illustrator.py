"""Exercise macOS routing and resumable batches with mocked Apple Events."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'plugins/cell_su7/skills/cell_su7/scripts'
sys.path.insert(0,str(SCRIPTS))
import run_illustrator as runner

with tempfile.TemporaryDirectory() as directory:
    operations=[]
    def fake_invoke(script,work):
        if script.startswith('(function'):
            return 'fixture.ai|Layer%201'
        config=json.loads(script.split('=',1)[1].split(';\n',1)[0])
        operations.append(config['operation'])
        if config['operation']=='draw':
            payload=json.loads(Path(config['batchJsonPath']).read_text(encoding='utf-8'))
            assert any(atom['kind']=='text' for atom in payload['atoms'])
        if config['operation']=='save':
            Path(config['outputAi']).write_bytes(b'mocked AI')
            return 'OK|documentName=fixture.ai'
        if config['operation']=='export': Path(config['outputPng']).write_bytes(b'mocked PNG')
        return 'OK|mocked'
    args=['runner','--input-svg',str(ROOT/'tests/fixtures/editable.svg'),'--output-root',directory]
    with patch.object(sys,'argv',args),patch.object(runner.platform,'system',return_value='Darwin'),patch.object(runner,'invoke_mac',fake_invoke):
        assert runner.main()==0
        assert runner.main()==0  # Reconcile completed batches against native objects.
    assert operations==['draw','normalize','save','export']*2
    state=json.loads((Path(directory)/'shibielujing1/.illustrator-cache/playback.json').read_text(encoding='utf-8'))
    assert state['target_layer']=='Layer 1' and all(b['completed'] for b in state['batches'])
    with patch.object(runner.subprocess,'run') as mock:
        mock.return_value.returncode=0
        mock.return_value.stdout='OK|mock'
        runner.invoke_mac('1+1',Path(directory))
        command=mock.call_args.args[0]
        assert command[0]=='osascript' and 'do javascript' in command[-1] and 'is running' in command[-1]
print('MAC_ILLUSTRATOR_MOCK_OK|routing=applescript|resume=reconciled|desktop-tested=false')
