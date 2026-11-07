"""One-job Python receiver. No scheduler, no second upload, no background drawing."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

SCRIPTS = Path(__file__).resolve().parent
STATE = 'receive-state.json'


def read(root):
    return json.loads((Path(root)/STATE).read_text(encoding='utf-8'))


def save(root, state):
    temp = Path(root)/'receive-state.tmp'
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(Path(root)/STATE)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def lock(root, name):
    with (Path(root)/name).open('a+b') as stream:
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def api(action, **arguments):
    # All credentials remain inside the existing platform adapter.
    if os.name == 'nt':
        command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                   str(SCRIPTS/'xiaomiao.ps1'), action]
        names = {'image_path':'-ImagePath', 'image_id':'-ImageId', 'output_path':'-OutputPath'}
    else:
        command = [sys.executable, str(SCRIPTS/'xiaomiao.py'), action]
        names = {key:'--'+key.replace('_','-') for key in arguments}
    for key, value in arguments.items():
        command.extend([names[key], str(value)])
    result = subprocess.run(command, capture_output=True, timeout=120,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Adapter '+action+' failed; original job retained')
    if action == 'download':
        return {'ok':True}
    return json.loads(result.stdout.decode('utf-8-sig'))


def bridge_for(thread_id):
    from desktop_bridge import Bridge
    return Bridge(caller_thread_id=thread_id, submit_thread_ids=[thread_id], rpc_timeout=25)


def origin(bridge, thread_id):
    doc = bridge._desktop_tool('read_thread', {'threadId':thread_id, 'turnLimit':1,
                              'includeOutputs':False, 'maxOutputCharsPerItem':0})
    if doc.get('thread', {}).get('id') != thread_id:
        raise RuntimeError('Original chat identity could not be verified')
    return doc['thread']


def probe(thread_id):
    bridge = bridge_for(thread_id)
    try:
        origin(bridge, thread_id)
        if 'send_message_to_thread' not in bridge._available_tools:
            raise RuntimeError('Desktop wake tool unavailable')
        return {'desktop_reachable':True, 'origin_thread':thread_id, 'sends_performed':0}
    finally:
        bridge.close()


def prepare(root, *, thread_id, application, image=None, image_id=None, text_manifest=None,
            credits=1, approve_high_cost=False, authorize_wake=False, call=api):
    root = Path(root).resolve()
    if not authorize_wake:
        raise ValueError('Original-chat wake authorization required')
    thread_id = str(uuid.UUID(thread_id))
    if credits < 1 or (credits > 1 and not approve_high_cost):
        raise ValueError('CREDIT_CONFIRM_REQUIRED')
    if image_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', image_id):
        raise ValueError('Invalid existing image id')
    root.mkdir(parents=True, exist_ok=True)
    with lock(root, 'submit.lock'):
        if (root/STATE).exists():
            old = read(root)
            if old['thread_id'] != thread_id or old['application'] != application:
                raise ValueError('Existing job belongs to a different chat or backend')
            if image_id and old.get('image_id') != image_id:
                raise ValueError('Existing image id mismatch')
            if image and old.get('input_sha256') != digest(image):
                raise ValueError('Input changed; existing job retained')
            if not old.get('image_id'):
                raise ValueError('Upload acknowledgement unknown; reconcile before retry, do not re-upload')
            return old
        if not image_id and not image:
            raise ValueError('Prepared image or existing image id required')
        state = {'thread_id':thread_id, 'application':application, 'image_id':image_id,
                 'wake_authorized':True, 'wake_state':'pending', 'nonce':uuid.uuid4().hex,
                 'status':'waiting' if image_id else 'submitting', 'created_at':time.time(),
                 'output_svg':str(root/'received-vector.svg'), 'estimated_credits':credits}
        if image:
            image = Path(image).resolve()
            state['input_sha256'] = digest(image)
            saved_input = root/('recognition-input'+image.suffix)
            if image != saved_input:
                shutil.copy2(image, saved_input)
            state['input_image'] = str(saved_input)
        if text_manifest:
            target = root/'text-manifest.json'
            if Path(text_manifest).resolve() != target:
                shutil.copy2(text_manifest, target)
            state['text_manifest'] = str(target)
        save(root, state)  # Durable before any potentially charged request.
        if not image_id:
            try:
                reply = call('upload', image_path=state['input_image'])
                returned = reply.get('image_id')
                if not isinstance(returned, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', returned):
                    raise ValueError('Missing image id')
                state.update(image_id=returned, status='waiting')
                save(root, state)
            except Exception:
                state['status'] = 'submit_unknown'
                save(root, state)
                raise
        return state


def receive(root, state, call=api):
    if state.get('svg_sha256'):
        if digest(state['output_svg']) != state['svg_sha256']:
            raise ValueError('Received SVG hash changed')
        return True
    reply = call('status', image_id=state['image_id'])
    state['remote_status'] = reply.get('status')
    if reply.get('status') in {'failed','expired','rejected'}:
        state['status'] = 'attention'
        save(root, state)
        raise ValueError('Remote job ended without a usable result')
    if reply.get('status') != 'completed':
        save(root, state)
        return False
    temp = Path(root)/'received-vector.part.svg'
    call('download', image_id=state['image_id'], output_path=temp)
    from validate_vector_svg import audit_svg
    audit = audit_svg(temp, strict_ids=False, allow_raster=False)
    (Path(root)/'received-vector-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    if audit['status'] != 'PASS':
        raise ValueError('Downloaded result failed vector validation')
    temp.replace(state['output_svg'])
    state.update(status='ready', svg_sha256=digest(state['output_svg']),
                 credits_left=reply.get('credits_left'), received_at=time.time())
    save(root, state)
    return True


def wake(root, state, bridge_factory=bridge_for):
    if (Path(root)/'stop.request').exists():
        return False
    if state['wake_state'] in {'sent','acknowledged','uncertain'}:
        return True
    if state['wake_state'] == 'sending':
        state.update(wake_state='uncertain', status='wake_uncertain')
        save(root, state)
        return True
    if not state.get('wake_authorized') or not state.get('svg_sha256'):
        raise ValueError('Cannot wake before verified receipt and authorization')
    if digest(state['output_svg']) != state['svg_sha256']:
        raise ValueError('Received SVG hash mismatch')
    bridge = bridge_factory(state['thread_id'])
    try:
        thread = origin(bridge, state['thread_id'])
        status = thread.get('status') or {}
        kind = status.get('type') if isinstance(status, dict) else status
        if kind in {'active','inProgress','running'}:
            return False
        if (Path(root)/'stop.request').exists():
            return False
        prompt = (f"cell_su7 的 Python 接收器已收到并校验原任务 {state['image_id']} 的矢量结果。\n"
                  f"任务目录：{Path(root).resolve()}\n接续标记：{state['nonce']}\n"
                  f"先按 {SCRIPTS.parent/'SKILL.md'} 的原对话接续规则处理。"
                  "读取 receive-state.json，核对原对话、任务编号、SVG摘要，并运行 receive_and_wake.py ack。"
                  "沿用已选 PPT/Illustrator，若有 text-manifest 先恢复可编辑文字，再继续校验与绘图。"
                  "只使用已收到的结果，不重新上传、不重复去水印、不重复扣费、不创建定时任务。"
                  "如果用户后来要求停止，保留结果并停止绘图。")
        state.update(wake_state='sending', status='wake_sending')
        save(root, state)
        try:
            reply = bridge.submit(state['thread_id'], prompt)
            if not reply.get('queued') or reply.get('thread_id') != state['thread_id']:
                raise RuntimeError('No matching wake acknowledgement')
        except Exception:
            state.update(wake_state='uncertain', status='wake_uncertain')
            save(root, state)  # Never blindly resend an ambiguously acknowledged message.
            return True
        state.update(wake_state='sent', status='wake_sent', wake_sent_at=time.time())
        save(root, state)
        return True
    finally:
        bridge.close()


def worker(root, timeout=86400, interval=15):
    root = Path(root).resolve()
    with lock(root, 'receiver.lock'):
        deadline = time.monotonic()+timeout
        failures = 0
        while time.monotonic() < deadline:
            state = read(root)
            if (root/'stop.request').exists():
                state['status']='stopped';save(root,state);return state
            if state['wake_state'] in {'sent','acknowledged','uncertain'}:
                return state
            if state['status'] in {'attention','submit_unknown'}:
                return state
            try:
                if receive(root, state) and wake(root, state):
                    return read(root)
                failures = 0
            except Exception as error:
                failures += 1
                state['last_error'] = type(error).__name__
                if failures >= 12 or state['status']=='attention':
                    state['status']='attention';save(root,state);return state
                save(root,state)
            # Polling is inside this one Python process, not a scheduled task/chat turn.
            for _ in range(max(1, interval)):
                if (root/'stop.request').exists(): break
                time.sleep(1)
        state=read(root);state.update(status='attention',last_error='ReceiverTimeout');save(root,state)
        return state


def launch(root):
    command=[sys.executable, str(Path(__file__).resolve()), 'worker', '--job-dir', str(Path(root).resolve())]
    kwargs={'stdin':subprocess.DEVNULL, 'stdout':subprocess.DEVNULL, 'stderr':subprocess.DEVNULL}
    if os.name=='nt':
        kwargs['creationflags']=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    else:
        kwargs['start_new_session']=True
    return subprocess.Popen(command, **kwargs).pid


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['start','worker','status','stop','resume','ack','probe'])
    p.add_argument('--job-dir',type=Path)
    p.add_argument('--thread-id',default=os.environ.get('CODEX_THREAD_ID'))
    p.add_argument('--application',choices=['ppt','ai'])
    p.add_argument('--input-image',type=Path)
    p.add_argument('--image-id')
    p.add_argument('--text-manifest',type=Path)
    p.add_argument('--estimated-credits',type=int,default=1)
    p.add_argument('--approve-high-cost',action='store_true')
    p.add_argument('--authorize-wake',action='store_true')
    p.add_argument('--nonce')
    a=p.parse_args()
    if a.action=='probe':
        result=probe(a.thread_id)
    else:
        if not a.job_dir: p.error('--job-dir is required')
        root=a.job_dir.resolve()
        if a.action=='start':
            if not a.application or not a.authorize_wake: p.error('--application and --authorize-wake are required')
            if a.estimated_credits>1 and not a.approve_high_cost: p.error('CREDIT_CONFIRM_REQUIRED')
            probe(a.thread_id)  # Fail before upload if the actual desktop bridge is unavailable.
            result=prepare(root,thread_id=a.thread_id,application=a.application,image=a.input_image,
                           image_id=a.image_id,text_manifest=a.text_manifest,credits=a.estimated_credits,
                           approve_high_cost=a.approve_high_cost,authorize_wake=a.authorize_wake)
            result={**result,'receiver_pid':launch(root)}
        elif a.action=='worker':
            result=worker(root)
        else:
            result=read(root)
            if a.action!='status' and a.thread_id!=result['thread_id']:
                raise ValueError('Only the original chat may control this receiver')
            if a.action=='stop':
                (root/'stop.request').write_text('User stopped this job',encoding='utf-8')
                result={'stop_requested':True,'image_id':result['image_id']}
            elif a.action=='resume':
                if result['wake_state'] in {'sending','uncertain'}:
                    raise ValueError('Reconcile existing wake message before resume')
                (root/'stop.request').unlink(missing_ok=True)
                result['status']='ready' if result.get('svg_sha256') else 'waiting'
                save(root,result);result={**result,'receiver_pid':launch(root)}
            elif a.action=='ack':
                if not a.nonce or a.nonce!=result['nonce']:
                    raise ValueError('Wrong continuation nonce')
                if digest(result['output_svg'])!=result.get('svg_sha256'):
                    raise ValueError('Received SVG hash mismatch')
                (root/'wake-received.json').write_text(json.dumps({'nonce':a.nonce,'thread_id':a.thread_id}),encoding='utf-8')
                result={'acknowledged':True,'image_id':result['image_id']}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
