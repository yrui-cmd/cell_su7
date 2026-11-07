import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'plugins/cell_su7/skills/cell_su7/scripts'
sys.path.insert(0,str(SCRIPTS))
import receive_and_wake as r

THREAD='11111111-1111-4111-8111-111111111111'
SVG=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path id="p" d="M0 0 L10 0 L10 10 Z"/></svg>'


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'job'
        self.calls=[]
    def tearDown(self):self.tmp.cleanup()
    def api(self,action,**args):
        self.calls.append(action)
        if action=='upload':return {'image_id':'img_test'}
        if action=='status':return {'status':'completed','credits_left':7}
        if action=='download':Path(args['output_path']).write_bytes(SVG);return {'ok':True}
    def prepare(self,**kwargs):
        return r.prepare(self.root,thread_id=THREAD,application='ppt',image_id='img_test',
                         authorize_wake=True,call=self.api,**kwargs)
    def test_existing_job_is_never_uploaded_and_wake_is_once_after_valid_receipt(self):
        state=self.prepare();self.assertTrue(r.receive(self.root,state,self.api))
        self.assertEqual(self.calls,['status','download'])
        sends=[]
        class Bridge:
            def _desktop_tool(self,*args,**kwargs):return {'thread':{'id':THREAD,'status':{'type':'idle'}}}
            def submit(self,thread,prompt):sends.append((thread,prompt));return {'queued':True,'thread_id':thread}
            def close(self):pass
        self.assertTrue(r.wake(self.root,state,lambda t:Bridge()))
        self.assertTrue(r.wake(self.root,r.read(self.root),lambda t:Bridge()))
        self.assertEqual(len(sends),1)
        self.assertEqual(state['credits_left'],7)
    def test_corrupt_result_never_marks_ready(self):
        state=self.prepare()
        def bad(action,**args):
            result=self.api(action,**args)
            if action=='download':Path(args['output_path']).write_text('<html>bad</html>')
            return result
        with self.assertRaisesRegex(ValueError,'validation'):r.receive(self.root,state,bad)
        self.assertNotIn('svg_sha256',r.read(self.root))
    def test_no_wake_before_receipt_or_when_stopped(self):
        state=self.prepare()
        with self.assertRaises(ValueError):r.wake(self.root,state)
        (self.root/'stop.request').touch()
        self.assertFalse(r.wake(self.root,state))
    def test_unknown_upload_is_fenced_against_repeat(self):
        image=Path(self.tmp.name)/'input.png';image.write_bytes(b'fixture')
        attempts=[]
        def lost(*args,**kwargs):attempts.append(1);raise TimeoutError()
        kwargs=dict(thread_id=THREAD,application='ppt',image=image,authorize_wake=True,call=lost)
        with self.assertRaises(TimeoutError):r.prepare(self.root,**kwargs)
        with self.assertRaisesRegex(ValueError,'unknown'):r.prepare(self.root,**kwargs)
        self.assertEqual(len(attempts),1)
    def test_unknown_wake_reply_is_not_resent(self):
        state=self.prepare();r.receive(self.root,state,self.api)
        sends=[]
        class Bridge:
            def _desktop_tool(self,*args,**kwargs):return {'thread':{'id':THREAD,'status':'idle'}}
            def submit(self,*args):sends.append(1);raise TimeoutError()
            def close(self):pass
        r.wake(self.root,state,lambda t:Bridge())
        self.assertEqual(r.read(self.root)['wake_state'],'uncertain')
        r.wake(self.root,r.read(self.root),lambda t:Bridge())
        self.assertEqual(len(sends),1)
    def test_busy_chat_waits_without_sending(self):
        state=self.prepare();r.receive(self.root,state,self.api)
        class Bridge:
            def _desktop_tool(self,*args,**kwargs):return {'thread':{'id':THREAD,'status':{'type':'active'}}}
            def submit(self,*args):raise AssertionError('No send while busy')
            def close(self):pass
        self.assertFalse(r.wake(self.root,state,lambda t:Bridge()))
    def test_changed_received_file_blocks_wake(self):
        state=self.prepare();r.receive(self.root,state,self.api)
        Path(state['output_svg']).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'hash'):r.wake(self.root,state)
    def test_high_cost_rejected_before_network_or_files(self):
        with self.assertRaisesRegex(ValueError,'CREDIT_CONFIRM'):self.prepare(credits=2)
        self.assertFalse(self.root.exists());self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
