import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from console_core import ROOT,RunManager,ReferenceStore
from server import make_handler
class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.manager=RunManager(Path(cls.tmp.name),launcher=lambda *a:None,preflight=lambda:{'ready':True});cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.manager,ReferenceStore(),'test-session-token'));threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.base='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
 def call(self,path,body=None,token='test-session-token',origin=None):
  headers={'X-Demo-Token':token,'Content-Type':'application/json'}
  if origin:headers['Origin']=origin
  req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
  try:r=urllib.request.urlopen(req);return r.status,r.read(),dict(r.headers)
  except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
 def test_bootstrap_separates_historical_scopes(self):
  status,body,_=self.call('/api/bootstrap');d=json.loads(body);self.assertEqual(status,200);self.assertEqual(d['overview']['formal']['recorded'],114);self.assertEqual(len(d['reviews']),58)
 def test_forged_action_token_rejected(self):self.assertEqual(self.call('/api/generate',{},token='wrong')[0],403)
 def test_cross_origin_mutation_rejected(self):self.assertEqual(self.call('/api/generate',{},origin='https://other.example')[0],403)
 def test_traversal_and_private_source_are_not_served(self):
  for url in ['/api/file?origin=reference&path=../../console_core.py','/api/file?origin=unknown&path=a','/source/console_core.py','/../console_core.py']:
   self.assertEqual(self.call(url)[0],404)
 def test_generation_calls_real_generator(self):
  status,body,_=self.call('/api/generate',{});self.assertEqual(status,201);self.assertEqual(json.loads(body)['executable'],4)
 def test_duplicate_run_rejected_then_interrupted_export(self):
  s,b,_=self.call('/api/runs',{'profile':'quick'});self.assertEqual(s,201);id=json.loads(b)['id']
  self.assertEqual(self.call('/api/runs',{'profile':'quick'})[0],409)
  self.assertEqual(self.call('/api/jobs/'+id+'/stop',{})[0],200)
  self.assertEqual(json.loads(self.call('/api/jobs/'+id)[1])['state'],'INTERRUPTED')
  code,data,headers=self.call('/api/jobs/'+id+'/export');self.assertEqual(code,200);self.assertTrue(data.startswith(b'PK'));self.assertIn('application/zip',headers['Content-Type'])
 def test_worksheet_download_and_source_readable(self):
  status,body,headers=self.call('/api/file?origin=reference&path=documents/HUMAN_REVIEW_WORKSHEET.csv');self.assertEqual(status,200);self.assertIn('attachment',headers['Content-Disposition']);self.assertIn(b'Human_Decision',body)
  self.assertEqual(self.call('/source/model_oracles.py')[0],200)
 def test_video_range_supported_if_companion_exists(self):
  video=ROOT.parents[1]/'outputs/Group7_D3_Optimization_Evidence/demo/Group7_Deliverable3_Optimized_Demo.mp4'
  if not video.exists():
   self.assertEqual(self.call('/video')[0],404);return
  req=urllib.request.Request(self.base+'/video',headers={'Range':'bytes=0-31'})
  with urllib.request.urlopen(req) as r:self.assertEqual(r.status,206);self.assertEqual(len(r.read()),32)
