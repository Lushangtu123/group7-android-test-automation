"""Actual isolated Chrome checks of the local UI through its observed DOM."""
import base64,json,time,urllib.request
from pathlib import Path
import websocket
OUT=Path(__file__).resolve().parent
class Browser:
 def __init__(self):
  pages=json.load(urllib.request.urlopen('http://127.0.0.1:9232/json/list'));page=next(p for p in pages if p['type']=='page');self.ws=websocket.create_connection(page['webSocketDebuggerUrl'],suppress_origin=True,timeout=30);self.seq=0;self.errors=[];self.call('Page.enable');self.call('Runtime.enable')
 def call(self,method,params=None):
  self.seq+=1;id=self.seq;self.ws.send(json.dumps({'id':id,'method':method,'params':params or {}}))
  while True:
   r=json.loads(self.ws.recv())
   if r.get('method')=='Runtime.exceptionThrown':self.errors.append(r['params'])
   if r.get('id')==id:
    if 'error' in r:raise RuntimeError(r['error'])
    return r.get('result',{})
 def js(self,code):
  r=self.call('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True})
  if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
  return r.get('result',{}).get('value')
 def size(self,width,height):self.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':1,'mobile':False})
 def shot(self,name):
  r=self.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(OUT/name).write_bytes(base64.b64decode(r['data']))
if __name__=='__main__':
 b=Browser();b.size(1600,1100);b.call('Page.navigate',{'url':'http://127.0.0.1:8770/'});time.sleep(1);print(b.js("({title:document.title,heading:document.querySelector('h1')?.textContent,errors:document.querySelector('#toast')?.textContent})"));b.shot('overview_desktop.png');b.ws.close()
