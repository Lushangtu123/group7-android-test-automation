"""Run the approved four-test plan through the actual browser controls."""
import json,time,sys,urllib.request,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from browser_check import Browser,OUT
BASE='http://127.0.0.1:8770'
STAGE=os.environ.get('ACCEPTANCE_STAGE','initial');PREFIX='' if STAGE=='initial' else STAGE+'_'
def api(path):
 with urllib.request.urlopen(BASE+path) as f:return json.load(f)
b=Browser();b.size(1920,1080);b.call('Page.navigate',{'url':BASE});time.sleep(.5)
def shot(name):b.shot(PREFIX+name)
assert b.js("document.querySelector('#repeats').value")=='2'
b.js("document.querySelector('#model-button').click();document.querySelector('#generate').click()")
time.sleep(.6);assert b.js("document.querySelector('#generation-result').textContent.includes('16 coordinates / 4 executable')")
shot('actual_generator.png');previous={j['id'] for j in api('/api/jobs')};b.js("document.querySelector('#model-dialog .close').click();document.querySelector('#start').click()")
deadline=time.monotonic()+20;job=None
while time.monotonic()<deadline:
 jobs=api('/api/jobs')
 fresh=[j for j in jobs if j['id'] not in previous]
 if fresh:job=fresh[0];break
 time.sleep(.5)
assert job and job['planned']==4
id=job['id'];(OUT/(PREFIX+'LIVE_ACCEPTANCE_RUN.json')).write_text(json.dumps(job,indent=2));print('STARTED',id,flush=True)
captured=set();frames={};observations=[];reloaded=False;start=time.monotonic();appium_visible=False
while time.monotonic()-start<900:
 snapshot=api('/api/jobs/'+id)
 metrics=b.js('window.liveFrameMetrics||[]')
 for m in metrics:frames[(m['sequence'],m['captured'])]=m
 view=b.js("({state:document.querySelector('#run-state').textContent,camera:document.querySelector('#camera-status').textContent,answer:document.querySelector('#answer').textContent,attempt:document.querySelector('#attempt').textContent,python:document.querySelector('#python-tab').getAttribute('aria-selected'),alert:document.querySelector('#alert').textContent})")
 observations.append({'at':time.time(),**view})
 for event in snapshot.get('events',[]):
  key=(event.get('attempt_id'),event.get('event'))
  if event['event']=='TURN_START' and key not in captured and view['camera']=='DEVICE LIVE':
   shot(event['app']+'_repeat'+str(event['repeat'])+'_live.png');captured.add(key)
  if event['event']=='TURN_DONE' and key not in captured:
   shot(event['app']+'_repeat'+str(event['repeat'])+'_captured.png');captured.add(key)
 if not appium_visible and len(frames)>10:
  b.js("document.querySelector('#appium-tab').click()");time.sleep(.1);assert b.js("document.querySelector('#logs').textContent.includes('[HTTP]')");shot('actual_appium_live.png');b.js("document.querySelector('#python-tab').click()");appium_visible=True
 if not reloaded and len(snapshot.get('attempts',[]))>=1 and snapshot['state']=='RUNNING':
  b.call('Page.reload',{'ignoreCache':True});time.sleep(.8);assert len(api('/api/jobs'))==len(previous)+1;reloaded=True
 if snapshot['state'] in ('COMPLETED','INTERRUPTED','PROCESS_ERROR'):
  time.sleep(.8);shot('live_final.png');break
 time.sleep(.7)
else:raise TimeoutError('Acceptance is still running; evidence and worker are preserved')
frames=list(frames.values());deltas=[m['delay_ms'] for m in frames]
result={'run_id':id,'job':snapshot,'browser_errors':b.errors,'frame_count_observed':len(frames),'unique_frame_sequences':len(set(m['sequence'] for m in frames)),'capture_to_browser_mean_ms':round(sum(deltas)/len(deltas),1) if deltas else None,'capture_to_browser_p95_ms':sorted(deltas)[min(len(deltas)-1,int(len(deltas)*.95))] if deltas else None,'appium_http_visible_during_run':appium_visible,'browser_reloaded_without_duplicate_worker':reloaded,'frame_metrics':frames,'view_observations':observations}
(OUT/(PREFIX+'LIVE_ACCEPTANCE_REPORT.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['job','frame_metrics','view_observations']},indent=2),flush=True);print('OUTCOMES',snapshot['counts'],flush=True);b.ws.close()
