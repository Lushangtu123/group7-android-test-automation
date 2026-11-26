"""Loopback-only presentation console; fixed actions, no shell command API."""
import argparse,csv,hashlib,io,json,mimetypes,os,re,secrets,sys,threading,zipfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote
from console_core import ROOT,ReferenceStore,RunManager,safe_join,public_text,preflight,preview_allowed,readjson,events
from console_core import atomic
from live_services import DeviceMirror,job_guard,read_log

def make_handler(manager,reference,token,mirror=None):
 def save_mirror(id,stats):
  try:atomic(manager.directory(id)/('mirror_statistics_'+stats['stream_id']+'.json'),stats)
  except (ValueError,OSError):pass
 mirror=mirror or DeviceMirror(guard=lambda id:job_guard(manager,id),on_end=save_mirror)
 class Handler(BaseHTTPRequestHandler):
  device_mirror=mirror
  def log_message(self,*args):pass
  def respond(self,data,status=200,kind='application/json; charset=utf-8',headers=None):
   if not isinstance(data,bytes):data=public_text(json.dumps(data,ensure_ascii=False)).encode()
   self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
   for k,v in (headers or {}).items():self.send_header(k,v)
   self.end_headers();self.wfile.write(data)
  def host_allowed(self):
   # Only the loopback names this server is reached by. A page served from another
   # hostname that resolves to 127.0.0.1 (DNS rebinding) is refused before any route.
   port=str(self.server.server_port)
   return self.headers.get('Host','') in ('127.0.0.1:'+port,'localhost:'+port)
  def do_GET(self):
   if not self.host_allowed():return self.respond({'error':'Open the console at http://127.0.0.1:'+str(self.server.server_port)},421)
   try:self.get()
   except (ValueError,KeyError,FileNotFoundError) as e:self.respond({'error':str(e)},404)
   except (BrokenPipeError,ConnectionResetError):pass
   except Exception as e:self.respond({'error':public_text(str(e))},500)
  def get(self):
   url=urlparse(self.path);q=parse_qs(url.query);path=url.path
   if path.startswith('/api/mirror/') or path.endswith('/logs'):
    if self.headers.get('X-Demo-Token')!=token:return self.respond({'error':'Local session token required'},403)
   if path=='/api/mirror/status':return self.respond(mirror.status())
   if path=='/api/mirror/frame':
    view=mirror.frame()
    if not view:return self.respond({'error':'Current frame withheld','mirror':mirror.status()},409)
    return self.respond(view['bytes'],kind='image/png',headers={'X-Frame-Captured-Utc':view['captured_utc'],'X-Frame-Sequence':str(view['sequence']),'X-Frame-Attempt':view.get('attempt_id') or ''})
   if path=='/api/bootstrap':return self.respond({'token':token,'overview':reference.overview(),'definitions':manager.definitions(),'jobs':manager.jobs(),'samples':reference.samples(),'reviews':reference.reviews(),'repeats':reference.repeats()})
   if path=='/api/health':return self.respond(preflight())
   if path=='/api/jobs':return self.respond(manager.jobs())
   if path.startswith('/api/jobs/'):
    parts=path.strip('/').split('/');id=parts[2]
    if len(parts)==3:return self.respond(manager.snapshot(id))
    if len(parts)==4 and parts[3]=='preview':
     view=manager.preview(id)
     if not view:return self.respond({'error':'No verified current-prompt frame yet'},404)
     if q.get('meta'):return self.respond({k:v for k,v in view.items() if k!='bytes'})
     return self.respond(view['bytes'],kind='image/png')
    if len(parts)==4 and parts[3]=='export':return self.export(id)
    if len(parts)==4 and parts[3]=='logs':return self.respond(read_log(manager.directory(id),q.get('source',['python'])[0],int(q.get('after',['0'])[0])))
   if path=='/api/detail':
    item=reference.details(q.get('id',[''])[0]);return self.respond(item or {'error':'No recorded detail available'},200 if item else 404)
   if path=='/api/file':
    origin=q.get('origin',[''])[0];rel=q.get('path',[''])[0]
    if origin=='reference':root=reference.root
    elif origin.startswith('job:'):root=manager.directory(origin[4:])
    else:raise ValueError('Unknown evidence origin')
    p=safe_join(root,rel)
    if not p.is_file():raise FileNotFoundError('Evidence file unavailable')
    if p.suffix=='.png':
     if origin.startswith('job:'):
      xml=p.with_suffix('.xml');prompts=[s for d in manager.definitions() for g in d['conversations'] for s in g]
      if not xml.is_file() or not preview_allowed(xml.read_text(),prompts):return self.respond({'error':'Image withheld: account or prompt ownership could not be verified'},403)
     return self.respond(p.read_bytes(),kind='image/png')
    if p.suffix.lower() not in {'.json','.jsonl','.csv','.xml','.log','.md','.txt','.py'}:raise ValueError('Unsupported public evidence type')
    kind='text/plain; charset=utf-8';headers={}
    if p.suffix=='.csv':kind='text/csv; charset=utf-8';headers={'Content-Disposition':f'attachment; filename="{p.name}"'}
    return self.respond(public_text(p.read_text(encoding='utf-8-sig')).encode(),kind=kind,headers=headers)
   if path.startswith('/source/'):
    name=path.split('/')[-1]
    if name not in ('model_oracles.py','oracles.py'):raise ValueError('Unknown source reference')
    return self.respond(public_text((ROOT/'engine/group7_auto'/name).read_text()).encode(),kind='text/plain; charset=utf-8')
   if path=='/video':
    # Never duplicate or re-encode the existing reviewed MP4.
    p=ROOT.parents[1]/'outputs/Group7_D3_Optimization_Evidence/demo/Group7_Deliverable3_Optimized_Demo.mp4'
    if not p.exists():raise FileNotFoundError('Original video is not available here; use the companion evidence package')
    size=p.stat().st_size;start,end=0,size-1;status=200;headers={'Accept-Ranges':'bytes'}
    value=self.headers.get('Range')
    if value:
     match=re.fullmatch(r'bytes=(\d+)-(\d*)',value)
     if not match:return self.respond({'error':'Unsupported range'},416)
     start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
     if start>end:return self.respond({'error':'Range out of bounds'},416)
     status=206;headers['Content-Range']=f'bytes {start}-{end}/{size}'
    with p.open('rb') as f:f.seek(start);data=f.read(end-start+1)
    return self.respond(data,status,kind='video/mp4',headers=headers)
   if path.startswith('/api/'):return self.respond({'error':'Route not found'},404)
   asset='index.html' if path=='/' else unquote(path.lstrip('/'));p=safe_join(ROOT/'static',asset)
   if not p.is_file():return self.respond({'error':'Page not found'},404)
   kind=mimetypes.guess_type(p.name)[0] or 'application/octet-stream';return self.respond(p.read_bytes(),kind=kind+('; charset=utf-8' if kind.startswith('text/') or kind=='application/javascript' else ''))
  def do_POST(self):
   if not self.host_allowed():return self.respond({'error':'Open the console at http://127.0.0.1:'+str(self.server.server_port)},421)
   try:
    if self.headers.get('X-Demo-Token')!=token:return self.respond({'error':'Reload the local console before using run controls'},403)
    origin=self.headers.get('Origin')
    if origin and origin not in ('http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)):return self.respond({'error':'Local console origin required'},403)
    size=int(self.headers.get('Content-Length','0'))
    if size>8192:return self.respond({'error':'Request too large'},413)
    value=json.loads(self.rfile.read(size) or b'{}')
    if self.path=='/api/generate':return self.respond(manager.generate(),201)
    if self.path=='/api/runs':
     job=manager.start(value);mirror.start(job['id']);return self.respond(job,201)
    if self.path=='/api/mirror/start':
     id=value.get('run_id');job=manager.snapshot(id)
     if job['state'] not in ('RUNNING','STOPPING'):raise RuntimeError('Only an active real run can start the device mirror')
     return self.respond(mirror.start(id))
    if self.path=='/api/mirror/stop':return self.respond(mirror.stop())
    if self.path.startswith('/api/jobs/') and self.path.endswith('/stop'):
     id=self.path.split('/')[3];job=manager.stop(id);mirror.stop();return self.respond(job)
    return self.respond({'error':'Action not found'},404)
   except (ValueError,json.JSONDecodeError) as e:self.respond({'error':str(e)},400)
   except RuntimeError as e:self.respond({'error':str(e)},409)
   except Exception as e:self.respond({'error':public_text(str(e))},500)
  def export(self,id):
   root=manager.directory(id);snapshot=manager.snapshot(id)
   if snapshot['state'] not in ('COMPLETED','INTERRUPTED','PROCESS_ERROR'):return self.respond({'error':'Wait for the run to end before exporting'},409)
   buf=io.BytesIO();hashes={};withheld=[]
   with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
    prompts=[s for d in manager.definitions() for g in d['conversations'] for s in g]
    for p in sorted(root.rglob('*')):
     if not p.is_file() or '__pycache__' in p.parts:continue
     rel=p.relative_to(root).as_posix()
     if p.suffix=='.png':
      xml=p.with_suffix('.xml')
      if not xml.is_file() or not preview_allowed(xml.read_text(),prompts):withheld.append(rel);continue
      data=p.read_bytes()
     elif p.suffix.lower() in {'.py','.sh','.js','.mjs','.css','.html'}:
      data=p.read_text().replace(str(Path.home()),'/Users/DEMO_USER').encode()
     elif p.suffix.lower() in {'.json','.jsonl','.csv','.xml','.log','.txt','.md'}:data=public_text(p.read_text()).encode()
     else:continue
     hashes[rel]={'raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'export_sha256':hashlib.sha256(data).hexdigest()};z.writestr(rel,data)
    z.writestr('EXPORT_PROVENANCE.json',json.dumps({'scope':'NEW_DEMO_RUN_NOT_FORMAL114','raw_originals_modified':False,'privacy_derivative':True,'hashes':hashes,'withheld_unverified_images':withheld,'note':'Historical counts are not updated. Raw source/proof hashes refer to original runtime bytes.'},indent=2))
   return self.respond(buf.getvalue(),kind='application/zip',headers={'Content-Disposition':f'attachment; filename="Group7_Demo_{id}.zip"'})
 return Handler

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8770);parser.add_argument('--runtime',type=Path);parser.add_argument('--open',action='store_true');a=parser.parse_args()
 if a.open and a.runtime is None:
  import urllib.request,webbrowser
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{a.port}/api/bootstrap',timeout=2) as response:existing=json.load(response)
   if isinstance(existing.get('definitions'),list) and 'overview' in existing and 'token' in existing:
    webbrowser.open(f'http://127.0.0.1:{a.port}');print('Opened the existing Group 7 console.');return
  except (OSError,ValueError):pass
 manager=RunManager(a.runtime);server=ThreadingHTTPServer(('127.0.0.1',a.port),make_handler(manager,ReferenceStore(),secrets.token_urlsafe(32)))
 url=f'http://127.0.0.1:{a.port}';print('Group7 demo console: '+url,flush=True)
 if a.open:
  import webbrowser;webbrowser.open(url)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.RequestHandlerClass.device_mirror.stop();server.server_close()
if __name__=='__main__':main()
