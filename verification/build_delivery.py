"""Verify provenance and build only the separate live-demonstration delivery."""
import csv,hashlib,io,json,platform,re,subprocess,sys,urllib.request,zipfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'verification';sys.path.insert(0,str(ROOT))
from console_core import public_text,private_names
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
before=json.loads((OUT/'PRESERVATION_BEFORE.json').read_text());preserved={}
for rel,expected in before.items():
 actual=sha(PROJECT/rel);assert actual==expected,rel;preserved[rel]=actual
write('PRESERVATION_AFTER.json',preserved)
videos=[]
for rel,expected in [('outputs/Group7_D3_Completion_Evidence/demo/Group7_Deliverable3_Demo.mp4','d753e00a96df2484fa6a09e3977639b41f86475db18ce4ced025b64974fd39d5'),('outputs/Group7_D3_Optimization_Evidence/demo/Group7_Deliverable3_Optimized_Demo.mp4','2e8315b1b79a61e372a4527e7664205b7046d8b02d79671f80e60cce679b409c')]:
 assert sha(PROJECT/rel)==expected;videos.append({'path':rel,'sha256':expected,'unchanged':True})
engine_count=0
with zipfile.ZipFile(PROJECT/'outputs/Group7_D3_Optimization_Evidence.zip') as z:
 prefix='Group7_D3_Optimization_Evidence/extension_source/'
 for n in z.namelist():
  if n.startswith(prefix) and not n.endswith('/'):
   assert (ROOT/'engine'/n[len(prefix):]).read_bytes()==z.read(n);engine_count+=1
for row in json.loads((ROOT/'reference/SOURCE_MAPPING.json').read_text()):assert sha(ROOT/row['demo_relative'])==row['sha256']
formal=json.loads((ROOT/'reference/data.json').read_text())['formal'];assert len(formal)==114 and Counter(r['status'] for r in formal)=={'PASS':37,'REVIEW':58,'ERROR':19}
with (ROOT/'reference/documents/HUMAN_REVIEW_WORKSHEET.csv').open(encoding='utf-8-sig') as f:reviews=list(csv.DictReader(f))
assert len(reviews)==58 and not any(r.get('Human_Decision') or r.get('Reviewer') or r.get('Review_Date') for r in reviews)
def command(args):
 p=subprocess.run(args,capture_output=True,text=True);return p.stdout.strip() if p.returncode==0 else None
host={'captured_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'architecture':platform.machine(),'python':sys.version,'macos':command(['sw_vers','-productVersion']),'cpu':command(['sysctl','-n','machdep.cpu.brand_string'])}
try:
 with urllib.request.urlopen('http://127.0.0.1:4723/status') as f:host['appium_server']=json.load(f)
except OSError:host['appium_server']=None
driver=PROJECT/'outputs/Group7_D3_Mac_Emulator_Project/.tools/appium-home/node_modules/appium-uiautomator2-driver/package.json'
if driver.exists():host['uiautomator2_version']=json.loads(driver.read_text())['version']
write('HOST_ENVIRONMENT.json',host)
runs=[];source_rows=[];exports=[];acceptances=[]
for stage,name in [('initial','LIVE_ACCEPTANCE_REPORT.json'),('final','final_LIVE_ACCEPTANCE_REPORT.json')]:
 a=json.loads((OUT/name).read_text());acceptances.append(a);id=a['run_id'];d=ROOT/'runtime/runs'/id;job=json.loads((d/'job.json').read_text());summary=json.loads((d/'summary.json').read_text());meta=json.loads((d/'execution_metadata.json').read_text());details=[json.loads(l) for l in (d/'response_details.jsonl').read_text().splitlines()]
 assert job['state']=='COMPLETED' and len(details)==4 and summary['status_counts']=={'PASS':4}
 assert Counter((r['application'],r['repeat']) for r in details)=={('chatgpt',1):1,('chatgpt',2):1,('gemini',1):1,('gemini',2):1}
 assert not a['browser_errors'] and a['appium_http_visible_during_run'] and a['browser_reloaded_without_duplicate_worker']
 seen=Counter(f['attempt_id'] for f in a['frame_metrics']);assert all(seen[r['attempt_id']]>0 for r in details)
 manifest=d/'console_source_sha256.json'
 if stage=='final':
  assert manifest.exists()
  for rel,expected in json.loads(manifest.read_text()).items():assert sha(d/'console_snapshot'/rel)==sha(ROOT/rel)==expected,rel
 for rel,expected in json.loads((d/'source_sha256.json').read_text()).items():assert sha(d/'source_snapshot'/rel)==expected
 stats=[json.loads(p.read_text()) for p in d.glob('mirror_statistics_*.json')]
 runs.append({'stage':stage,'run_id':id,'scope':job['scope'],'planned':4,'completed':4,'counts':summary['status_counts'],'worker_wall_seconds':meta['wall_seconds'],'browser_frame_count':a['frame_count_observed'],'capture_to_browser_mean_ms':a['capture_to_browser_mean_ms'],'capture_to_browser_p95_ms':a['capture_to_browser_p95_ms'],'frames_by_attempt':dict(seen),'mirror_statistics':stats,'attempts':[{'attempt_id':r['attempt_id'],'application':r['application'],'repeat':r['repeat'],'status':r['status'],'complete_turns':r['completed_turns'],'planned_turns':r['planned_turns']} for r in details]})
 source_rows.append({'stage':stage,'run_id':id,'worker_sha256':sha(d/'worker_snapshot.py'),'engine_manifest_sha256':sha(d/'source_sha256.json'),'console_manifest_sha256':sha(manifest) if manifest.exists() else '', 'version_note':'Final frozen console and engine sources verified' if stage=='final' else 'Initial acceptance before console snapshot and stream lifecycle refinements; engine and worker snapshots retained'})
 with urllib.request.urlopen('http://127.0.0.1:8770/api/jobs/'+id+'/export') as f:data=f.read()
 target=OUT/('Group7_Live_Run_'+id+'.zip');target.write_bytes(data)
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  assert z.testzip() is None;provenance=json.loads(z.read('EXPORT_PROVENANCE.json'))
  for rel,hashes in provenance['hashes'].items():
   assert digest(z.read(rel))==hashes['export_sha256'];assert sha(d/rel)==hashes['raw_sha256']
   if Path(rel).suffix!='.png':
    text=z.read(rel).decode();assert not any(re.search(r'(?<![A-Za-z0-9])'+re.escape(n)+r'(?![A-Za-z0-9])',text,re.I) for n in private_names()),rel
  exports.append({'stage':stage,'file':target.name,'sha256':digest(data),'bytes':len(data),'entries':len(z.namelist()),'withheld_images':len(provenance['withheld_unverified_images']),'raw_derivative_mappings_verified':True})
with (OUT/'EXECUTION_SOURCE_MAP.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(source_rows[0]));w.writeheader();w.writerows(source_rows)
browser=json.loads((OUT/'BROWSER_CHECKS.json').read_text());assert not browser['browser_errors']
report={'validated_utc':datetime.now(timezone.utc).isoformat(),'client_date':'2026-11-25','formal114':{'PASS':37,'FAIL':0,'REVIEW':58,'ERROR':19},'unsigned_human_reviews':58,'historical_model_extension':{'PASS':12,'FAIL':0,'REVIEW':1,'ERROR':3},'live_acceptance_runs':runs,'new_demo_total_only':{'planned':8,'completed':8,'PASS':8,'FAIL':0,'REVIEW':0,'ERROR':0},'local_checks_not_android_tests':{'python_console':45,'javascript':3,'unchanged_engine':197,'browser_checks':len(browser['checks']),'browser_errors':0},'unchanged_historical_file_count':len(preserved),'historical_archives_verified':sum(k.endswith('.zip') for k in preserved),'unchanged_engine_files':engine_count,'original_videos':videos,'exports':exports,'limitations':['This acceptance exercised generated GEN-009, not all four selectable scenarios or a new formal114 batch.','The mirror targets5fps, not30/60fps, and hides navigation/unverified pages. Preview frames remain in memory.','The XML-based privacy guard is conservative; use the dedicated device and avoid manual private navigation.','Original 4/16 model coverage and unsigned formal human review remain unchanged.','No new Demo movie was recorded or edited.','Original runtime files are local; portable exports are documented privacy derivatives.']}
write('DELIVERY_REPORT.json',report)
if '--package' not in sys.argv:print(json.dumps(report,indent=2));sys.exit(0)
target=PROJECT/'outputs/Group7_Live_Demo.zip'
if target.exists():raise FileExistsError('Refusing to overwrite an existing live-demo delivery')
selected={'DELIVERY_REPORT.json','PRESERVATION_BEFORE.json','PRESERVATION_AFTER.json','EXECUTION_SOURCE_MAP.csv','HOST_ENVIRONMENT.json','BROWSER_CHECKS.json','backend_green.log','ui_logic_green.log','engine_regression.log','LIVE_ACCEPTANCE_REPORT.json','final_LIVE_ACCEPTANCE_REPORT.json','LIVE_ACCEPTANCE_RUN.json','final_LIVE_ACCEPTANCE_RUN.json','delivery_idle.png','delivery_completed.png','delivery_mobile.png'}|{r['file'] for r in exports}
files={};mapping={}
def add(relative,p):
 raw=p.read_bytes();data=raw
 if p.suffix in {'.json','.jsonl','.xml','.csv','.log','.md','.txt'}:data=public_text(raw.decode('utf-8-sig')).encode()
 if p.suffix not in {'.png','.zip'}:
  text=data.decode();assert str(Path.home()) not in text
  assert not any(re.search(r'(?<![A-Za-z0-9])'+re.escape(n)+r'(?![A-Za-z0-9])',text,re.I) for n in private_names()),relative
 files[relative]=data;mapping[relative]={'local_path':str(p.relative_to(ROOT)),'local_sha256':digest(raw),'package_sha256':digest(data),'privacy_derivative':raw!=data}
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts:continue
 rel=p.relative_to(ROOT)
 if rel.parts[0]=='runtime':continue
 if rel.parts[0]=='verification' and not (rel.name in selected or rel.suffix=='.py' or rel.name.startswith('final_') and rel.suffix=='.png'):continue
 add(str(rel),p)
for p in (ROOT/'runtime/generation').rglob('*'):
 if p.is_file():add('actual_generation/'+str(p.relative_to(ROOT/'runtime/generation')),p)
files['PACKAGE_SOURCE_MAPPING.json']=json.dumps({'mapping':mapping,'raw_runtime_excluded':True,'browser_profile_excluded':True,'note':'Archived hashes refer to original bytes. Package hashes identify any text privacy derivative. Two independent acceptance-run exports are included.'},indent=2).encode()
files['SHA256SUMS.txt']=''.join(digest(data)+'  '+name+'\n' for name,data in sorted(files.items())).encode()
with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
 for name,data in files.items():
  info=zipfile.ZipInfo('Group7_Live_Demo/'+name);info.create_system=3;info.external_attr=((0o100755 if name.endswith('.command') else 0o100644)<<16);info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 for name,data in files.items():assert z.read('Group7_Live_Demo/'+name)==data
qa={'path':str(target.relative_to(PROJECT)),'sha256':sha(target),'bytes':target.stat().st_size,'members':len(files),'crc_and_all_bytes_verified':True,'raw_runtime_included':False,'historical_evidence_preserved':True};write('PACKAGE_QA.json',qa);target.with_suffix('.zip.sha256').write_text(qa['sha256']+'  '+target.name+'\n');print(json.dumps(qa,indent=2))
