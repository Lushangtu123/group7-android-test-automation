"""Local demonstration services. Historical references are never written to."""
import csv,hashlib,importlib.util,io,json,os,re,shutil,signal,subprocess,sys,threading,time,uuid,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent
CASES=('MB-GEN-001','MB-GEN-008','MB-GEN-009','MB-GEN-013')
TERMINAL={'COMPLETED','INTERRUPTED','PROCESS_ERROR'}
def utc():return datetime.now(timezone.utc).isoformat()
ENGINE=str(ROOT/'engine')
def use_engine():
 # Add the engine to the import path once, not on every call.
 if ENGINE not in sys.path:sys.path.insert(0,ENGINE)
_DEFINITIONS=None
def case_definitions():
 """The four executable case definitions. They are fixed for the life of the process,
 so they are built once; callers get their own copy."""
 global _DEFINITIONS
 if _DEFINITIONS is None:
  use_engine();from group7_auto.model_based import concretize
  _DEFINITIONS=concretize()
 return json.loads(json.dumps(_DEFINITIONS))
def atomic(path,data):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(path)
def readjson(path,default=None):
 try:return json.loads(Path(path).read_text())
 except (FileNotFoundError,json.JSONDecodeError):return default

def validate_plan(value):
 if not isinstance(value,dict):raise ValueError('Run settings must be an object')
 if set(value)-{'profile','app','cases','repeats'}:raise ValueError('Unknown run setting')
 profile=value.get('profile','quick')
 if profile not in ('quick','full'):raise ValueError('Choose quick or full mode')
 if profile=='quick':
  for k,v in [('app','both'),('cases',['MB-GEN-009']),('repeats',1)]:
   if k in value and (value[k]!=v or k=='repeats' and type(value[k]) is not int):raise ValueError('Quick Demo runs GEN-009 once on each app')
  return {'profile':'quick','app':'both','cases':['MB-GEN-009'],'repeats':1}
 app=value.get('app','both');cases=value.get('cases',list(CASES));repeats=value.get('repeats',2)
 if app not in ('chatgpt','gemini','both'):raise ValueError('Unknown application')
 if not isinstance(cases,list) or not cases or any(x not in CASES for x in cases) or len(cases)!=len(set(cases)):raise ValueError('Choose distinct reviewed executable cases')
 if type(repeats) is not int or not 1<=repeats<=3:raise ValueError('Repeat count must be 1, 2 or 3')
 return {'profile':'full','app':app,'cases':cases,'repeats':repeats}

def safe_join(root,relative):
 root=Path(root).resolve();path=Path(str(relative))
 if path.is_absolute() or '..' in path.parts:raise ValueError('Invalid evidence path')
 result=(root/path).resolve()
 if not result.is_relative_to(root):raise ValueError('Evidence path outside directory')
 return result

def private_names():
 for path in (ROOT/'runtime/private_display_names.json',ROOT.parents[1]/'work/d3_private_account_names.json'):
  value=readjson(path,[])
  if isinstance(value,list) and value:return [n for n in value if isinstance(n,str) and n.strip()]
 return []

def public_text(text):
 text=str(text)
 lines=[];clipboard=False
 for line in text.splitlines(keepends=True):
  lower=line.lower();clip=any(n in lower for n in ('getclipboard','setclipboard','get_clipboard','set_clipboard'))
  if '-->' in line and '[HTTP]' in line:clipboard=clip
  elif clip:clipboard=True
  line=re.sub(r'("content"\s*:\s*")[A-Za-z0-9+/=]+(")',r'\1[CLIPBOARD REDACTED]\2',line)
  if clipboard:
   line=re.sub(r'("(?:value|text)"\s*:\s*")(?:\\.|[^"\\])*(")',r'\1[CLIPBOARD REDACTED]\2',line)
   if 'am broadcast' in line:line=line.split('am broadcast',1)[0]+'am broadcast [CLIPBOARD ARGUMENTS REDACTED]\n'
  lines.append(line)
 text=''.join(lines)
 text=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}','[EMAIL REDACTED]',text)
 text=re.sub(r'/Users/[^/\s"\']+','/Users/DEMO_USER',text)
 text=re.sub(r'(?i)("(?:access_token|refresh_token|id_token|password|client_secret|cookie)"\s*:\s*")[^"]*(")',r'\1[REDACTED]\2',text)
 text=re.sub(r'(?i)(Authorization\s*:\s*Bearer\s+)\S+',r'\1[REDACTED]',text)
 for name in private_names():
  text=re.sub(r'(^|[^A-Za-z0-9]|\\[nrtb])'+re.escape(name)+r'(?=$|[^A-Za-z0-9])',r'\1[ACCOUNT REDACTED]',text,flags=re.I)
 return text

def preview_allowed(xml,prompts):
 if '<!DOCTYPE' in xml or '<!ENTITY' in xml:return False
 try:nodes=list(ET.fromstring(xml).iter())
 except ET.ParseError:return False
 for n in nodes:
  text=(n.get('text') or '')+' '+(n.get('content-desc') or '')
  if re.search(r'[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}',text):return False
  if any(x in n.get('resource-id','').lower() for x in ('account_name','account_email','account_display_name','profile_name','account_switcher')):return False
  if n.get('text') in ('Google Account','Manage your Google Account','Quick Share') or 'google account:' in text.lower():return False
  if any(re.search(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])',text,re.I) for name in private_names()):return False
 return any((n.get('text') in prompts or n.get('content-desc') in prompts) and n.get('displayed','true')!='false' for n in nodes)

FINAL_STAGE=4
def frame_rank(name):
 """Order of a saved turn screenshot: (conversation, turn, stage), or None if it is not one.
 Stages: before_send 1, after_send 2, native_view_NN 3.NN, final capture 4."""
 m=re.search(r'_conversation(\d+)_turn(\d+)(_before_send|_after_send|_native_view_(\d+))?\.png$',name)
 if not m:return None
 stage=FINAL_STAGE if not m[3] else 1 if m[3]=='_before_send' else 2 if m[3]=='_after_send' else 3+int(m[4])/1000
 return (int(m[1]),int(m[2]),stage)

def appium_server_url(config):
 return str(config.get('server_url') or 'http://127.0.0.1:4723').rstrip('/')

def sdk_paths():
 sdk=Path(os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT') or Path.home()/'Library/Android/sdk')
 return sdk,Path(shutil.which('adb') or sdk/'platform-tools/adb')
def command(args,timeout=8):
 try:
  r=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout)
  return r.returncode,r.stdout.strip(),r.stderr.strip()
 except (OSError,subprocess.TimeoutExpired) as e:return -1,'',str(e)
def preflight():
 sdk,adb=sdk_paths();checks=[]
 def check(name,ok,detail,instruction=''):checks.append({'name':name,'ok':bool(ok),'detail':detail,'instruction':instruction})
 check('Python mobile client',importlib.util.find_spec('appium') is not None,sys.executable,'Start with Start Demo.command to use the existing Python environment.')
 check('Android SDK / ADB',adb.is_file(),public_text(str(adb)),'Set ANDROID_HOME to your existing SDK directory.')
 device='emulator-5554';config=readjson(ROOT/'engine/data/android_appium_config.local.json',{})
 device=config.get('apps',{}).get('chatgpt',{}).get('capabilities',{}).get('appium:udid',device)
 if adb.is_file():
  code,text,_=command([adb,'-s',device,'get-state']);boot=command([adb,'-s',device,'shell','getprop','sys.boot_completed'])[1] if code==0 else ''
  check('Pixel 7 emulator',code==0 and text=='device' and boot=='1',f'{device}: '+('booted' if boot=='1' else 'not ready'),f'Open the existing Group7_Pixel7_API35 device in Android Studio, or run: "{sdk}/emulator/emulator" -avd Group7_Pixel7_API35 -no-audio -dns-server 8.8.8.8,1.1.1.1')
  if code==0:
   for name,pkg in [('ChatGPT','com.openai.chatgpt'),('Gemini','com.google.android.apps.bard')]:
    c,t,_=command([adb,'-s',device,'shell','pm','path',pkg]);check(name+' installed',c==0 and 'package:' in t,pkg,'Use the already installed, logged-in test app. Login is checked by the actual UI run.')
 # Same server the engine connects to (appium_adapter reads server_url from this config).
 server=appium_server_url(config)
 try:
  with urllib.request.urlopen(server+'/status',timeout=3) as f:data=json.load(f)
  ready=data.get('value',{}).get('ready',False);detail='Appium at '+server
 except Exception:ready=False;detail='Appium is not responding at '+server
 check('Appium server',ready,detail,'Start the existing server: bash "Start Appium.command". No software is installed.')
 return {'ready':all(c['ok'] for c in checks),'checks':checks,'checked_utc':utc(),'note':'Readiness does not prove app login, current selector compatibility, or backend health. Each live run checks network and UI readiness.'}

class ReferenceStore:
 def __init__(self):self.root=ROOT/'reference';self.data=readjson(self.root/'data.json',{})
 def overview(self):return {'formal':readjson(self.root/'formal_statistics.json',{}),'extension':readjson(self.root/'extension_statistics.json',{}),'complexity':readjson(self.root/'complexity.json',{}),'sample_count':len(self.data.get('samples',[]))}
 def repeats(self):return self.data.get('formal',[])
 def reviews(self):
  with (self.root/'documents/HUMAN_REVIEW_WORKSHEET.csv').open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 def details(self,attempt):return next((d for d in self.data.get('details',[]) if d['attempt_id']==attempt),None)
 def samples(self):return self.data.get('samples',[])

def loadcsv(path):
 try:
  with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 except FileNotFoundError:return []
def events(path):
 try:lines=path.read_text().splitlines()
 except FileNotFoundError:return []
 result=[]
 for line in lines:
  try:result.append(json.loads(line))
  except json.JSONDecodeError:pass
 return result

class RunManager:
 def __init__(self,directory=None,launcher=None,preflight=preflight):
  self.root=Path(directory or ROOT/'runtime');self.root.mkdir(exist_ok=True,parents=True);self.lock=threading.RLock();self.processes={};self.cache={};self.launcher=launcher;self.preflight=preflight
  for path in self.root.glob('runs/*/job.json'):
   self._reconcile(path.parent)
   job=readjson(path,{})
   if job.get('state') in ('RUNNING','STOPPING'):
    pid=job.get('pid');alive=False
    if pid:
     try:os.kill(pid,0);alive=True
     except OSError:pass
    if not alive:job.update(state='INTERRUPTED',ended_utc=utc(),reason='Console restarted after the previous worker ended without finalization');atomic(path,job)
 def jobs(self):
  with self.lock:
   result=[]
   for p in self.root.glob('runs/*/job.json'):
    self._reconcile(p.parent);result.append(readjson(p,{}))
   return sorted(result,key=lambda j:j['started_utc'],reverse=True)
 def _reconcile(self,directory):
  job=readjson(directory/'job.json',{});meta=readjson(directory/'execution_metadata.json',{})
  if job.get('state') not in TERMINAL and meta.get('ended_utc'):
   job.update(state='INTERRUPTED' if meta.get('interrupted') else ('COMPLETED' if meta.get('exit_code')==0 and (directory/'summary.json').exists() else 'PROCESS_ERROR'),ended_utc=meta['ended_utc'],exit_code=meta.get('exit_code'));atomic(directory/'job.json',job)
 def start(self,value):
  plan=validate_plan(value)
  busy='An Android run is already active. Stop or wait for it before starting another.'
  with self.lock:
   if any(j['state'] not in TERMINAL for j in self.jobs()):raise RuntimeError(busy)
  # The readiness check runs adb and Appium probes (tens of seconds at worst), so it runs
  # without the lock; other requests keep working meanwhile. The active-run check repeats
  # under the lock, so two concurrent starts still create only one run.
  health=self.preflight()
  if not health.get('ready'):raise RuntimeError('Environment is not ready. Check the readiness panel before starting.')
  with self.lock:
   if any(j['state'] not in TERMINAL for j in self.jobs()):raise RuntimeError(busy)
   id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8];directory=self.root/'runs'/id;directory.mkdir(parents=True,exist_ok=False)
   job={'id':id,'state':'RUNNING','plan':plan,'started_utc':utc(),'scope':'NEW_DEMO_RUN_NOT_FORMAL114','planned':len(plan['cases'])*(2 if plan['app']=='both' else 1)*plan['repeats'],'pid':None,'capture_label':'Continuous current-device mirror; saved screenshots are separate evidence'};atomic(directory/'job.json',job)
   authored=[p for name in ('console_core.py','server.py','live_services.py','live_worker.py') if (p:=ROOT/name).exists()]+[p for p in (ROOT/'static').rglob('*') if p.is_file()]
   hashes={}
   for p in authored:
    relative=p.relative_to(ROOT);target=directory/'console_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);hashes[str(relative)]=hashlib.sha256(target.read_bytes()).hexdigest()
   atomic(directory/'console_source_sha256.json',hashes)
   if self.launcher:self.launcher(id,plan,directory)
   else:
    handle=(directory/'worker.log').open('xb');proc=subprocess.Popen([sys.executable,str(ROOT/'live_worker.py'),'--directory',str(directory)],stdout=handle,stderr=subprocess.STDOUT,start_new_session=True);handle.close();self.processes[id]=proc;job['pid']=proc.pid;atomic(directory/'job.json',job)
    threading.Thread(target=self._wait,args=(id,proc),daemon=True).start()
   return job
 def _wait(self,id,proc):
  code=proc.wait()
  with self.lock:
   path=self.directory(id)/'job.json';job=readjson(path,{})
   if job.get('state') in TERMINAL:return
   interrupted=job.get('state')=='STOPPING' or (self.directory(id)/'stop_requested').exists()
   self.mark_ended(id,interrupted=interrupted,code=code)
 def directory(self,id):
  if not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}',id):raise ValueError('Invalid run ID')
  path=self.root/'runs'/id
  if not (path/'job.json').exists():raise ValueError('Run not found')
  return path
 def mark_ended(self,id,interrupted=False,code=0):
  with self.lock:
   p=self.directory(id)/'job.json';job=readjson(p,{})
   job.update(state='INTERRUPTED' if interrupted else ('COMPLETED' if code==0 and (p.parent/'summary.json').exists() else 'PROCESS_ERROR'),ended_utc=utc(),exit_code=code);atomic(p,job)
 def stop(self,id):
  with self.lock:
   directory=self.directory(id);job=readjson(directory/'job.json',{})
   if job['state'] in TERMINAL:return job
   (directory/'stop_requested').touch();job['state']='STOPPING';atomic(directory/'job.json',job)
   proc=self.processes.get(id)
   if proc and proc.poll() is None:proc.send_signal(signal.SIGINT)
   elif job.get('pid'):
    # A restored worker recognizes the marker and checks it at every WebDriver request.
    pass
   else:self.mark_ended(id,interrupted=True)
   return readjson(directory/'job.json')
 def _parsed(self,path,loader):
  # The page polls twice a second; re-parse a file only when its size or time changed.
  try:st=path.stat();key=(st.st_size,st.st_mtime_ns)
  except FileNotFoundError:return []
  with self.lock:
   hit=self.cache.get(path)
   if hit and hit[0]==key:return list(hit[1])
  value=loader(path)
  with self.lock:self.cache[path]=(key,value)
  return list(value)
 def snapshot(self,id):
  d=self.directory(id);self._reconcile(d);job=readjson(d/'job.json');all_events=self._parsed(d/'execution.log',events);rows=self._parsed(d/'attempts.csv',loadcsv);turns=self._parsed(d/'turn_checkpoints.jsonl',events);details=self._parsed(d/'response_details.jsonl',events)
  active=next((e for e in reversed(all_events) if e.get('event')=='CONVERSATION_PREPARE'),None)
  return {**job,'events':all_events[-120:],'attempts':rows,'turns':turns,'details':details,'summary':readjson(d/'summary.json'),'active_attempt':active,'elapsed_seconds':round((datetime.now(timezone.utc)-datetime.fromisoformat(job['started_utc'])).total_seconds()) if job['state'] not in TERMINAL else None,'counts':{s:sum(r['status']==s for r in rows) for s in ('PASS','FAIL','REVIEW','ERROR')}}
 def generate(self):
  with self.lock:
   id=uuid.uuid4().hex[:12];folder=self.root/'generation'/id;folder.mkdir(parents=True,exist_ok=False)
   # Existing generator is independent of Appium and writes only this new folder.
   use_engine()
   from group7_auto.augmentation import export_generated_cases
   from group7_auto.model_based import export_executable
   begin=time.monotonic();a=export_generated_cases(folder/'generated_candidates.csv');b=export_executable(folder/'model_based_extension.csv');result={'id':id,'candidates':len(a),'executable':len(b),'elapsed_seconds':round(time.monotonic()-begin,6),'created_utc':utc(),'definitions':b,'coordinates':a,'remote_llm_call':False};atomic(folder/'generation.json',result);return result
 def preview(self,id):
  # Resolved so it compares with safe_join's resolved path when the runtime folder is behind a symlink.
  d=self.directory(id).resolve();snap=self.snapshot(id);active=snap['active_attempt']
  if not active:return None
  folder=safe_join(d,active['evidence_directory']);case=active['case'];definitions=self.definitions();prompts=[p for r in definitions if r['case_id']==case for g in r['conversations'] for p in g]
  candidates=[]
  for png in folder.glob('*.png'):
   if 'reset' in png.name or 'unused_notice' in png.name or frame_rank(png.name) is None:continue
   xml=png.with_suffix('.xml')
   if xml.is_file() and preview_allowed(xml.read_text(),prompts):candidates.append(png)
  if not candidates:return None
  # Latest turn first, then the latest stage of that turn. File times are not used to choose:
  # they change when a run folder is copied or unpacked.
  p=max(candidates,key=lambda p:frame_rank(p.name));conversation,turn,stage=frame_rank(p.name)
  recorded=next((t.get('captured_at_utc') for t in snap['turns'] if t.get('attempt_id')==active['attempt_id'] and t.get('conversation')==conversation and t.get('turn')==turn),None)
  captured=recorded if recorded and stage==FINAL_STAGE else datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()
  return {'path':str(p.relative_to(d)),'captured_utc':captured,'capture_time_source':'turn_checkpoint' if recorded and stage==FINAL_STAGE else 'file_modified_time','attempt_id':active['attempt_id'],'label':'Saved evidence frame — capture time shown','bytes':p.read_bytes()}
 def definitions(self):return case_definitions()
