import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from console_core import RunManager,ReferenceStore
from live_services import DeviceMirror
from server import make_handler
class LiveHttpTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.manager=RunManager(self.root,launcher=lambda *a:None,preflight=lambda:{'ready':True});self.mirror=DeviceMirror(capture=lambda:b'\x89PNG\r\n\x1a\nframe',guard=lambda _: {'allowed':True,'observed_epoch':10},clock=lambda:10)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.manager,ReferenceStore(),'token',mirror=self.mirror));threading.Thread(target=self.server.serve_forever,daemon=True).start();self.base='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.mirror.stop();self.server.shutdown();self.server.server_close();self.tmp.cleanup()
 def call(self,path,data=None,token='token'):
  request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-Demo-Token':token})
  try:
   with urllib.request.urlopen(request) as r:return r.status,r.read(),dict(r.headers)
  except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
 def test_frame_requires_session_token(self):self.assertEqual(self.call('/api/mirror/frame',token='wrong')[0],403)
 def test_frame_contains_capture_time_and_sequence(self):
  self.mirror.start('run',background=False);self.mirror.capture_once();status,data,headers=self.call('/api/mirror/frame');self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'image/png');self.assertIn('X-Frame-Captured-Utc',headers);self.assertEqual(headers['X-Frame-Sequence'],'1')
 def test_new_run_starts_mirror_and_stop_stops_it(self):
  status,data,_=self.call('/api/runs',{'profile':'full','cases':['MB-GEN-009'],'app':'both','repeats':2});self.assertEqual(status,201);job=json.loads(data);self.assertEqual(job['planned'],4);self.assertEqual(self.mirror.run_id,job['id']);self.call('/api/jobs/'+job['id']+'/stop',{});self.assertEqual(self.mirror.status()['state'],'OFF')
 def test_running_python_log_and_cursor_available(self):
  job=self.manager.start({'profile':'quick'});(self.manager.directory(job['id'])/'execution.log').write_text('actual event\n');code,data,_=self.call('/api/jobs/'+job['id']+'/logs?source=python&after=0');self.assertEqual(code,200);self.assertEqual(json.loads(data)['lines'],['actual event'])
 def test_export_keeps_executable_source_regex_bytes(self):
  import io,zipfile
  raw=b"pattern = r'/Users/[^/\\s]+'\n"
  job=self.manager.start({'profile':'quick'});(self.manager.directory(job['id'])/'source_module.py').write_bytes(raw);self.manager.mark_ended(job['id'],interrupted=True)
  code,data,_=self.call('/api/jobs/'+job['id']+'/export');self.assertEqual(code,200)
  with zipfile.ZipFile(io.BytesIO(data)) as z:self.assertEqual(z.read('source_module.py'),raw)
