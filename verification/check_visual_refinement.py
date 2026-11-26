"""Read-only UI checks for the light skin; no Android run is started."""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from visual_browser_check import Browser,OUT
ROOT=OUT.parent;baseline=json.loads((OUT/'VISUAL_BASELINE.json').read_text());checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(label,ok):
 if not ok:raise AssertionError(label)
 checks.append(label)
for name,expected in baseline['hashes'].items():
 if name not in ('static/index.html','static/style.css','original_delivery_zip'):check('unchanged '+name,sha(ROOT/name)==expected)
check('previous delivery ZIP unchanged',sha(ROOT.parents[1]/'outputs/Group7_Live_Demo.zip')==baseline['hashes']['original_delivery_zip'])
raw_before={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'runtime/runs').rglob('*') if p.is_file()}
b=Browser();b.size(1920,1080);b.call('Page.navigate',{'url':'http://127.0.0.1:8770/'});time.sleep(.5)
check('light paper background',b.js("getComputedStyle(document.body).backgroundColor==='rgb(244, 241, 233)'"))
check('main prompt and answer at least24px',b.js("['#prompt','#answer'].every(s=>parseFloat(getComputedStyle(document.querySelector(s)).fontSize)>=24)"))
check('actual log text at least20px',b.js("parseFloat(getComputedStyle(document.querySelector('#logs')).fontSize)>=20"))
check('live execution controls remain available',b.js("!document.querySelector('#start').disabled&&document.querySelector('#repeats').value==='2'&&document.querySelector('#case').options.length===4"))
check('idle view does not impersonate a live stream',b.js("document.querySelector('#camera-status').textContent==='VIEW OFF'"))
b.shot('refined_desktop_1920.png')
run=json.loads((OUT/'final_LIVE_ACCEPTANCE_RUN.json').read_text())['id'];b.js("document.querySelector('#saved').value='"+run+"';document.querySelector('#saved').dispatchEvent(new Event('change'))");time.sleep(.65)
check('preserved4case results still displayed',b.js("document.querySelectorAll('#outcomes [data-attempt]').length===4"))
b.js("document.querySelector('#appium-tab').click()");check('actual Appium log switch still works',b.js("document.querySelector('#logs').textContent.includes('[HTTP]')"))
b.js("document.querySelector('[data-attempt]').click()");check('full answer inspection still works',b.js("document.querySelector('#answer-dialog').open&&document.querySelector('#answer-detail').textContent.includes('Le chat dort.')"));b.js("document.querySelector('#answer-dialog .close').click()")
b.shot('refined_completed_desktop.png')
b.js("document.querySelector('#model-button').click()");check('model panel still opens',b.js("document.querySelector('#model-dialog').open"));b.js("document.querySelector('#model-dialog .close').click()")
b.size(390,844);time.sleep(.2);check('mobile page has no horizontal overflow',b.js('document.documentElement.scrollWidth<=innerWidth'));b.shot('refined_mobile.png');b.size(1600,1100);b.call('Page.navigate',{'url':'http://127.0.0.1:8770/'});time.sleep(.3);b.shot('refined_idle_desktop.png')
check('no browser JavaScript errors',not b.errors);b.ws.close()
check('all existing run evidence bytes unchanged',all(sha(ROOT/name)==expected for name,expected in raw_before.items()))
report={'changes':['static/index.html: header branding only','static/style.css: light visual skin and responsive layout'],'checks':checks,'browser_errors':b.errors,'new_android_tests':0,'existing_run_files_unchanged':len(raw_before),'backend_and_browser_javascript_unchanged':True,'previous_delivery_zip_unchanged':True,'evidence_note':'Earlier live acceptance results retain their original executed source snapshots. This visual refinement does not claim a new Android execution.'}
(OUT/'VISUAL_QA.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
