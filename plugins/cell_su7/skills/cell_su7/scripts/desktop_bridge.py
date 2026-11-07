"""Live desktop RPC bridge with explicitly scoped background submission.

Never use an isolated app-server's thread status as live execution authority.
"""
from collections import deque
import copy
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid


AUTHORIZED_SUBMIT_THREADS = frozenset()


_PIPE_RELAY = r'''
// Public Codex app-tool framing; sends are restricted to authorized target IDs.
const net=require('net'),readline=require('readline');
const paths=JSON.parse(process.argv[1]),MAX=8*1024*1024;
const submitThreads=new Set(JSON.parse(process.argv[2]));
const panel=JSON.parse(process.argv[3]);
let socket=null,queued=[],closed=false;
function frame(value){const b=Buffer.from(JSON.stringify(value));if(b.length>MAX)throw Error('frame too large');const h=Buffer.alloc(4);h.writeUInt32LE(b.length);return Buffer.concat([h,b]);}
function fail(message){if(closed)return;closed=true;process.stderr.write(message+'\n');if(socket)socket.destroy();process.exit(1);}
function allowed(v){if(v.method==='tools/list')return true;if(v.method!=='tools/call'||v.params?.namespace!=='codex_app')return false;
 if(['read_thread','wait_threads'].includes(v.params?.tool))return true;
 const a=v.params?.arguments;
 if(v.params?.tool==='open_in_codex')return panel.url&&v.params.threadId===panel.thread&&a&&Object.keys(a).length===2&&a.placement==='right'&&a.target&&Object.keys(a.target).length===2&&a.target.type==='browser'&&a.target.url===panel.url;
 return v.params?.tool==='send_message_to_thread'&&a&&submitThreads.has(a.threadId)&&typeof a.prompt==='string'&&a.prompt.trim()&&Object.keys(a).every(k=>['threadId','prompt'].includes(k));}
readline.createInterface({input:process.stdin}).on('line',line=>{
 try{const v=JSON.parse(line);if(!allowed(v))throw Error('scoped desktop bridge tool denied');
 const b=frame(v);if(socket)socket.write(b);else queued.push(b);}catch(e){fail(e.message);}
}).on('close',()=>{if(socket)socket.destroy();process.exit(0);});
function probe(path){return new Promise(resolve=>{
 let buffer=Buffer.alloc(0),done=false;
 const s=net.createConnection(path);
 const timer=setTimeout(()=>finish(false),700);
 function finish(ok){if(done)return;done=true;clearTimeout(timer);if(!ok)s.destroy();resolve(ok?s:null);}
 s.on('error',()=>{if(socket===s)fail('desktop pipe disconnected');else finish(false);});
 s.on('close',()=>{if(socket===s)fail('desktop pipe closed');else finish(false);});
 s.on('connect',()=>s.write(frame({id:0,jsonrpc:'2.0',method:'tools/list',params:{threadStartKind:'all'}})));
 s.on('data',chunk=>{
  buffer=Buffer.concat([buffer,chunk]);
  while(buffer.length>=4){
   const n=buffer.readUInt32LE(0);if(n>MAX){if(socket===s)fail('desktop frame too large');finish(false);return;}
   if(buffer.length<n+4)return;
   let v;try{v=JSON.parse(buffer.subarray(4,n+4).toString('utf8'));}catch(e){finish(false);return;}
   buffer=buffer.subarray(n+4);
   if(v.id===0){const ts=v.result?.tools;finish(Array.isArray(ts)&&ts.some(t=>t.namespace==='codex_app'&&t.name==='read_thread'));}
   else if(socket===s)process.stdout.write(JSON.stringify(v)+'\n');
  }
 });
 });}
(async()=>{
 // Prefer the inherited current app pipe. Discover only public named pipes.
 for(let i=0;i<paths.length;){
  const count=i===0?1:8;const group=await Promise.all(paths.slice(i,i+count).map(probe));i+=count;
  const chosen=group.find(Boolean);
  if(chosen){socket=chosen;for(const other of group)if(other&&other!==chosen)other.destroy();for(const b of queued)socket.write(b);queued=[];return;}
 }
 fail('No live Codex desktop app-tools pipe found');
})().catch(e=>fail(e.message));
'''


def _pipe_candidates():
    candidates = []
    inherited = os.environ.get('CODEX_APP_TOOLS_PIPE_PATH', '').strip()
    if inherited:
        candidates.append(inherited)
    try:
        candidates.extend('\\\\.\\pipe\\' + name for name in os.listdir('\\\\.\\pipe\\')
                          if name.startswith('codex-browser-use-'))
    except OSError:
        pass
    return list(dict.fromkeys(candidates))[:128]


def _node_executable():
    configured = os.environ.get('CODEX_MCP_NODE_PATH')
    if configured and Path(configured).is_file():
        return configured
    installed = shutil.which('node')
    if installed:
        return installed
    local = os.environ.get('LOCALAPPDATA')
    if local:
        runtime = Path(local) / 'OpenAI/Codex/runtimes/cua_node'
        candidates = [path for path in runtime.glob('*/bin/node.exe') if path.is_file()]
        if candidates:
            return str(max(candidates, key=lambda path: path.stat().st_mtime))
    standard = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    return str(standard) if standard.is_file() else None


class BridgeError(RuntimeError):
    def __init__(self, error):
        self.error = error
        self.code = error.get('code') if isinstance(error, dict) else None
        super().__init__(str(error))


class Bridge:
    def __init__(self, *, rpc_timeout=30, recent_turn_limit=8, caller_thread_id=None,
                 event_driven=False, submit_thread_ids=None, panel_url=None):
        self.exe = shutil.which('codex')
        self.submit_thread_ids = frozenset(AUTHORIZED_SUBMIT_THREADS if submit_thread_ids is None
                                           else submit_thread_ids)
        if panel_url is not None and not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}/[0-9a-f]{48}/',panel_url):
            raise ValueError('Only a local task progress URL is permitted')
        self.panel_url = panel_url
        self.rpc_timeout = rpc_timeout
        self.recent_turn_limit = recent_turn_limit
        self.event_driven = event_driven
        self._snapshots = {}
        self._snapshot_locks = {}
        self.serial = 0
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._pending = {}
        self._disconnected = False
        self._closed = False
        self.notifications = deque(maxlen=128)
        self.caller_thread_id = (caller_thread_id or os.environ.get('CELL_PIPELINE_CALLER_THREAD_ID')
                                 or os.environ.get('CODEX_THREAD_ID'))
        if not self.caller_thread_id:
            raise RuntimeError('Desktop read requires configured controller caller thread ID')
        node = _node_executable()
        if not node:
            raise RuntimeError('Node.js is required for the desktop pipe transport')
        self.process = subprocess.Popen([node, '-e', _PIPE_RELAY, json.dumps(_pipe_candidates()),
                                          json.dumps(sorted(self.submit_thread_ids)),
                                          json.dumps({"thread":self.caller_thread_id,"url":self.panel_url})],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        threading.Thread(target=self._read, daemon=True).start()
        try:
            catalog = self.call('tools/list', {'threadStartKind': 'all'})
            self._available_tools = {tool.get('name') for tool in catalog.get('tools', [])
                                     if tool.get('namespace') == 'codex_app'}
            if not any(tool.get('namespace') == 'codex_app' and tool.get('name') == 'read_thread'
                       for tool in catalog.get('tools', [])):
                raise RuntimeError('Connected pipe does not expose desktop read_thread')
            if event_driven and not any(tool.get('namespace') == 'codex_app' and tool.get('name') == 'wait_threads'
                                        for tool in catalog.get('tools', [])):
                raise RuntimeError('Connected pipe does not expose desktop wait_threads')
        except Exception:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    response = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(response, dict):
                    continue
                with self._lock:
                    target = self._pending.get(response.get('id'))
                    if target is not None and ('result' in response or 'error' in response):
                        target.put(response)
                    else:
                        self.notifications.append(response)
        except (OSError, ValueError):
            pass  # Closing our helper can interrupt a blocked stdout read.
        finally:
            with self._lock:
                self._disconnected = True
                for target in self._pending.values():
                    target.put({'disconnected': True})

    def send(self, value):
        with self._write_lock:
            if self._closed:
                raise RuntimeError('Codex bridge closed')
            self.process.stdin.write(json.dumps(value, ensure_ascii=False) + '\n')
            self.process.stdin.flush()

    def call(self, method, params, *, timeout=None):
        # Absolute deadline includes writing. Notifications cannot reset it.
        tool = params.get('tool')
        if method != 'tools/list' and not (method == 'tools/call' and params.get('namespace') == 'codex_app'
                and tool in {'read_thread', 'wait_threads', 'send_message_to_thread', 'open_in_codex'}):
            raise ValueError('Desktop bridge tool denied')
        if method == 'tools/call' and tool == 'open_in_codex':
            expected = {'placement':'right','target':{'type':'browser','url':self.panel_url}}
            if not self.panel_url or params.get('threadId') != self.caller_thread_id or params.get('arguments') != expected:
                raise ValueError('Progress panel outside authorized scope')
        if method == 'tools/call' and tool == 'send_message_to_thread':
            arguments = params.get('arguments') or {}
            if (arguments.get('threadId') not in self.submit_thread_ids
                    or set(arguments) != {'threadId', 'prompt'}
                    or not isinstance(arguments.get('prompt'), str) or not arguments['prompt'].strip()):
                raise ValueError('Desktop submission outside authorized scope')
        deadline = time.monotonic() + (self.rpc_timeout if timeout is None else timeout)
        target = queue.Queue()
        with self._lock:
            if self._disconnected or self._closed:
                raise RuntimeError('Codex shared daemon disconnected')
            self.serial += 1
            request_id = self.serial
            self._pending[request_id] = target
        try:
            # Pipe backpressure must not bypass the total deadline either.
            def write_request():
                try:
                    self.send({'id': request_id, 'jsonrpc': '2.0', 'method': method, 'params': params})
                except Exception as error:
                    target.put({'write_error': error})
            threading.Thread(target=write_request, daemon=True).start()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Codex RPC deadline exceeded: ' + method)
            try:
                response = target.get(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError('Codex RPC deadline exceeded: ' + method) from error
            if time.monotonic() > deadline:
                raise TimeoutError('Codex RPC deadline exceeded: ' + method)
            if response.get('disconnected'):
                raise RuntimeError('Codex shared daemon disconnected')
            if 'write_error' in response:
                raise RuntimeError('Codex RPC write failed') from response['write_error']
            if 'error' in response:
                raise BridgeError(response['error'])
            return response['result']
        finally:
            with self._lock:
                self._pending.pop(request_id, None)

    def _desktop_tool(self, tool, arguments, *, timeout=None):
        result = self.call('tools/call', {'namespace': 'codex_app', 'tool': tool,
            'arguments': arguments,
            'callerSource': 'codex', 'threadId': self.caller_thread_id,
            'turnId': 'controller-read-' + uuid.uuid4().hex,
            'callId': 'controller-read-' + uuid.uuid4().hex}, timeout=timeout)
        if result.get('success') is not True:
            raise RuntimeError('Desktop ' + tool + ' failed: ' + str(result)[:500])
        documents = []
        for item in result.get('contentItems', []):
            if item.get('type') == 'inputText':
                try:
                    value = json.loads(item.get('text', ''))
                except ValueError:
                    continue
                if isinstance(value, dict):
                    documents.append(value)
        if len(documents) != 1:
            raise RuntimeError('Desktop ' + tool + ' returned no unique document')
        return documents[0]

    def _read_full(self, thread_id, *, timeout=None):
        deadline = time.monotonic() + (self.rpc_timeout if timeout is None else timeout)
        arguments = {'threadId': thread_id,
            'turnLimit': 2 if self.event_driven else self.recent_turn_limit,
            'includeOutputs': True, 'maxOutputCharsPerItem': 2048}
        document = self._desktop_tool('read_thread', arguments, timeout=max(.001, deadline-time.monotonic()))
        # Native app sends arrive as attributed functionCallOutput. The ordinary
        # tool-output cap must not truncate the envelope used for token fencing.
        clipped_input = any(item.get('type') == 'functionCallOutput'
            and item.get('namespace') == 'codex_app' and item.get('name') == 'send_message_to_thread'
            and isinstance(item.get('output'), dict) and item['output'].get('truncated') is True
            for turn in document.get('turns', []) for item in turn.get('items', []))
        if clipped_input:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Desktop delegated input read deadline exceeded')
            # Verified current public tool maximum; retain truncated=true if a
            # still-larger envelope cannot be authenticated by native_messages.
            document = self._desktop_tool('read_thread', {**arguments, 'maxOutputCharsPerItem': 20000},
                                          timeout=remaining)
        if not isinstance(document.get('thread'), dict):
            raise RuntimeError('Desktop read_thread returned no thread metadata')
        thread = dict(document['thread'])
        if thread.get('id') != thread_id:
            raise RuntimeError('Desktop thread identity mismatch')
        turns = document.get('turns')
        if not isinstance(turns, list):
            raise RuntimeError('Invalid desktop turn page')
        page = document.get('page') or {}
        thread['turns'] = list(reversed(turns)) if page.get('order') == 'newest_first' else turns
        thread['history_truncated'] = bool(page.get('hasMore') or page.get('nextCursor'))
        thread['status_source'] = 'codex_desktop'
        # The desktop tool preserves full tool identity/arguments/command fields.
        # Only textual tool outputs are clipped, with their truncation flags kept.
        return thread

    @staticmethod
    def _compact_progress(poll):
        latest = poll.get('latestTurn') or {}
        marker = poll.get('latestToolMarker') or {}
        return (json.dumps(poll['thread'].get('status'), sort_keys=True),
                latest.get('id'), latest.get('status'), latest.get('completedAt'),
                poll.get('latestAssistantMessageId'), poll.get('latestToolMarkerId'),
                marker.get('status'))

    @staticmethod
    def _is_active(thread):
        status = thread.get('status') or {}
        kind = status.get('type') if isinstance(status, dict) else status
        turns = thread.get('turns') or []
        return kind in {'active', 'inProgress', 'running'} or bool(
            turns and turns[-1].get('status') in {'inProgress', 'running'})

    @classmethod
    def _apply_live_poll(cls, thread, poll, *, reused):
        """Conservative race handling: an observed active state wins over idle."""
        latest = poll.get('latestTurn') or {}
        compact = {'status': poll['thread'].get('status'), 'turns': [latest] if latest else []}
        compact_active = cls._is_active(compact)
        full_active = cls._is_active(thread)
        if reused or compact_active:
            thread['status'] = copy.deepcopy(poll['thread'].get('status'))
        if compact_active:
            # A compact active observation must never be hidden by old cached
            # idle data, or a full read that races with a newly started turn.
            if not cls._is_active({'status': thread['status']}):
                thread['status'] = {'type': 'active', 'activeFlags': []}
            matches = [turn for turn in thread['turns'] if turn.get('id') == latest.get('id')]
            if latest and matches:
                matches[-1].update(copy.deepcopy(latest))
            elif latest and not full_active:
                thread['turns'] = (thread['turns'] + [{**copy.deepcopy(latest), 'items': []}])[-2:]
        elif reused and latest:
            for turn in thread['turns']:
                if turn.get('id') == latest.get('id'):
                    turn.update(copy.deepcopy(latest))
        return thread

    def read(self, thread_id):
        if not self.event_driven:
            return self._read_full(thread_id)
        with self._lock:
            snapshot_lock = self._snapshot_locks.setdefault(thread_id, threading.Lock())
        # The controller normally uses one bridge per worker. Serialize reads
        # of the same target so an older cursor cannot overwrite a newer one.
        deadline = time.monotonic() + self.rpc_timeout
        if not snapshot_lock.acquire(timeout=max(0, deadline-time.monotonic())):
            raise TimeoutError('Desktop event snapshot deadline exceeded')
        try:
            cached = self._snapshots.get(thread_id)
            if cached is None:
                thread = self._read_full(thread_id, timeout=deadline-time.monotonic())
                thread.update(live_status_verified_at=time.time(), snapshot_reused=False,
                              wait_cursor=None)
                self._snapshots[thread_id] = {'thread': copy.deepcopy(thread), 'cursor': None,
                                             'progress': None}
                return thread
            target = {'threadId': thread_id, 'hostId': 'local'}
            if cached['cursor']:
                target['afterCursor'] = cached['cursor']
            # First compact snapshot primes its cursor immediately. Subsequent
            # waits wake early on completion/attention or return fresh compact
            # progress after at most ten seconds.
            remaining = deadline-time.monotonic()
            wait_ms = min(10000, max(0, int((remaining-1)*1000))) if cached['cursor'] else 0
            document = self._desktop_tool('wait_threads', {'targets': [target], 'timeoutMs': wait_ms},
                                          timeout=remaining)
            if document.get('errors'):
                raise RuntimeError('Desktop wait_threads could not verify target liveness')
            polls = [poll for poll in document.get('polls', []) if isinstance(poll, dict)
                     and isinstance(poll.get('thread'), dict) and poll['thread'].get('id') == thread_id]
            if len(polls) != 1 or not isinstance(polls[0].get('cursor'), str) or not polls[0]['cursor']:
                raise RuntimeError('Desktop wait_threads returned no authoritative target snapshot')
            poll = polls[0]
            progress = self._compact_progress(poll)
            changed = (poll.get('changed') is True or poll['cursor'] != cached['cursor']
                       or progress != cached['progress'])
            thread = (self._read_full(thread_id, timeout=deadline-time.monotonic()) if changed
                      else copy.deepcopy(cached['thread']))
            self._apply_live_poll(thread, poll, reused=not changed)
            thread.update(live_status_verified_at=time.time(), snapshot_reused=not changed,
                          wait_cursor=poll['cursor'])
            self._snapshots[thread_id] = {'thread': copy.deepcopy(thread), 'cursor': poll['cursor'],
                                         'progress': progress}
            return thread
        finally:
            snapshot_lock.release()

    def submit(self, thread_id, prompt):
        # The public desktop tool resumes dormant chats without UI navigation.
        # One call only: on timeout the durable caller fence must reconcile its
        # existing token. Never fall back to CLI queue or resend a lost response.
        if thread_id not in self.submit_thread_ids:
            raise ValueError('Desktop submission outside authorized scope')
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError('Submission prompt is empty')
        if 'send_message_to_thread' not in self._available_tools:
            raise RuntimeError('Desktop send_message_to_thread is unavailable')
        payload = self._desktop_tool('send_message_to_thread', {'threadId': thread_id, 'prompt': prompt})
        returned_thread = payload.get('threadId') or payload.get('thread_id')
        if returned_thread != thread_id:
            raise RuntimeError('Desktop submission target mismatch; reconcile existing token')
        turn = payload.get('turn') or {}
        turn_id = payload.get('turn_id') or payload.get('turnId') or (
            turn.get('id') if isinstance(turn, dict) else None)
        # Current desktop releases return threadId only. Preserve optional future
        # turn identity without claiming that a queue acknowledgement is a turn.
        self._snapshots.pop(thread_id, None)
        return {'queued': True, 'thread_id': thread_id, 'turn_id': turn_id,
                'response': payload, 'output': json.dumps(payload, ensure_ascii=False),
                'transport': 'codex_desktop_send_message_to_thread'}

    @staticmethod
    def wake(thread_id):
        """Compatibility hook: validate identity without activating a window."""
        return str(uuid.UUID(thread_id))

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._disconnected = True
            for target in self._pending.values():
                target.put({'disconnected': True})
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        for stream in (self.process.stdin, self.process.stdout):
            try:
                stream.close()
            except (AttributeError, OSError, ValueError):
                pass
