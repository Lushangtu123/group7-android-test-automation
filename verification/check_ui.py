"""Browser checks after real execution; does not start another Android test."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from browser_check import Browser,OUT
b=Browser();b.size(1920,1080);b.call('Page.navigate',{'url':'http://127.0.0.1:8770/'});time.sleep(.5);checks=[]
def check(name,ok):
 if not ok:raise AssertionError(name)
 checks.append(name)
check('default entry is the execution workbench',b.js("!!document.querySelector('.workbench')&&!document.querySelector('.steps')"))
check('default plan is both apps twice',b.js("document.querySelector('#application').value==='both'&&document.querySelector('#repeats').value==='2'"))
check('completed history does not autoplay as live',b.js("document.querySelector('#run-state').textContent==='IDLE'&&document.querySelector('#camera-status').textContent==='VIEW OFF'"))
check('log font is at least20px',b.js("parseFloat(getComputedStyle(document.querySelector('#logs')).fontSize)>=20"))
check('prompt and answer fonts are at least24px',b.js("['#prompt','#answer'].every(s=>parseFloat(getComputedStyle(document.querySelector(s)).fontSize)>=24)"))
b.shot('delivery_idle.png')
run=json.loads((OUT/'final_LIVE_ACCEPTANCE_RUN.json').read_text())['id']
b.js("document.querySelector('#saved').value='"+run+"';document.querySelector('#saved').dispatchEvent(new Event('change'))");time.sleep(.7)
check('all4 real outcomes selectable',b.js("document.querySelectorAll('#outcomes [data-attempt]').length===4"))
check('finished run has no live indicator',b.js("!document.querySelector('#camera-dot').classList.contains('on')"))
check('stop hidden and evidence export visible after completion',b.js("getComputedStyle(document.querySelector('#stop')).display==='none'&&getComputedStyle(document.querySelector('#export')).display!=='none'"))
b.js("document.querySelector('[data-attempt]').click()");check('complete answer dialog available',b.js("document.querySelector('#answer-dialog').open&&document.querySelector('#answer-detail').textContent.includes('Le chat dort.')"));b.js("document.querySelector('#answer-dialog .close').click()")
b.js("document.querySelector('#appium-tab').click()");time.sleep(.3);check('real Appium HTTP logs available',b.js("document.querySelector('#logs').textContent.includes('[HTTP]')"));b.shot('delivery_completed.png')
b.js("document.querySelector('#model-button').click()");check('model oracle visible',b.js("document.querySelector('#definition').textContent.includes('opt_translate_fr_cat')"));b.js("document.querySelector('#model-dialog .close').click()")
rect=b.js("(()=>{const r=document.querySelector('#fullscreen').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
for kind in ['mousePressed','mouseReleased']:b.call('Input.dispatchMouseEvent',{'type':kind,**rect,'button':'left','clickCount':1})
time.sleep(.2);check('fullscreen control works with actual browser input',b.js('!!document.fullscreenElement'));b.js('document.exitFullscreen()')
b.size(390,844);time.sleep(.2);check('mobile has no document horizontal overflow',b.js('document.documentElement.scrollWidth<=innerWidth'));b.shot('delivery_mobile.png');b.size(1920,1080)
b.call('Page.navigate',{'url':'http://127.0.0.1:8770/library/index.html#evidence'});time.sleep(.6);check('recorded library remains available and labelled',b.js("document.querySelectorAll('.sample-card').length===10&&document.querySelector('#evidence').textContent.includes('Recorded evidence')"))
check('no uncaught JavaScript errors',not b.errors)
(OUT/'BROWSER_CHECKS.json').write_text(json.dumps({'checks':checks,'browser_errors':b.errors},indent=2));print(json.dumps({'checks':checks,'browser_errors':b.errors},indent=2));b.call('Page.navigate',{'url':'http://127.0.0.1:8770/'});b.ws.close()
