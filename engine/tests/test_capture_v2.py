import json, unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake

class CaptureV2Regression(unittest.TestCase):
 def config(self,tmp):
  path=fake.TestFakeAppiumAdapter()._config(tmp)
  d=json.loads(path.read_text());d['apps']['chatgpt']['selectors']['assistant_response_after_prompt_xpath']='AFTER_USER:{prompt}'
  path.write_text(json.dumps(d));return path
 def test_clipped_previous_answer_is_not_a_new_turn(self):
  with TemporaryDirectory() as tmp:
   d=fake.FakeMobileDriver();original=d.find_elements
   d.find_elements=lambda by,value: [] if value.startswith('AFTER_USER:') else original(by,value)
   d.send_button.click=lambda:setattr(d,'responses',[fake.UIElement(d,'Prior answer clipped by viewport')])
   with self.assertRaises(TimeoutError):LiveAdapter(self.config(tmp),'chatgpt',driver=d).send('New question','TC-MEM-02','turn3',Path(tmp)/'shots')
 def test_identical_current_reply_is_fresh_if_after_current_user_anchor(self):
  with TemporaryDirectory() as tmp:
   d=fake.FakeMobileDriver();d.responses=[fake.UIElement(d,'Ottawa.')];old=d.find_elements
   new=fake.UIElement(d,'Ottawa.');d.find_elements=lambda by,value:[new] if value.startswith('AFTER_USER:') else old(by,value)
   d.send_button.click=lambda:None
   self.assertEqual(LiveAdapter(self.config(tmp),'chatgpt',driver=d).send('Again','TC-FA-01','turn2',Path(tmp)/'shots'),'Ottawa.')
 def test_copy_uses_current_response_scope(self):
  with TemporaryDirectory() as tmp:
   path=self.config(tmp);cfg=json.loads(path.read_text());s=cfg['apps']['chatgpt'];s['capture_mode']='copy';s['selectors']['copy_response_button']={'by':'id','value':'copy'};s['selectors']['response_copy_relative']={'by':'id','value':'localcopy'};path.write_text(json.dumps(cfg))
   d=fake.FakeMobileDriver();d.clipboard='';d.get_clipboard_text=lambda:d.clipboard;d.set_clipboard_text=lambda v:setattr(d,'clipboard',v)
   reply=fake.UIElement(d,'Current verified response');button=fake.UIElement(d);button.rect={'x':100,'y':500,'width':80,'height':80};button.click=lambda:setattr(d,'clipboard','Current verified response')
   reply.find_elements=lambda by,value:[button] if value=='localcopy' else [reply]
   old=d.find_elements;d.find_elements=lambda by,value:[reply] if value.startswith('AFTER_USER:') else ([] if value=='copy' else old(by,value))
   d.send_button.click=lambda:None
   self.assertEqual(LiveAdapter(path,'chatgpt',driver=d).send('Question','TC-FA-01','turn2',Path(tmp)/'shots'),'Current verified response')

 def test_safe_configured_drag_is_used_instead_of_accessibility_scroll(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());spec=cfg['apps']['chatgpt'];spec['selectors']['response_scroll_container']={'by':'id','value':'scroll'};spec['response_scroll_action']='mobile: dragGesture';spec['response_scroll_gesture']={'startX':540,'startY':1750,'endX':540,'endY':650,'speed':1200};path.write_text(json.dumps(cfg))
   d=fake.FakeMobileDriver();d.responses=[];d.send_button.click=lambda:None;old=d.find_elements;scroll=fake.UIElement(d);scroll.id='scroll';d.find_elements=lambda by,value:[scroll] if value=='scroll' else old(by,value);calls=[]
   def execute(name,args):
    calls.append(name);d.responses=[fake.UIElement(d,'Current answer')]
   d.execute_script=execute
   self.assertEqual(LiveAdapter(path,'chatgpt',driver=d).send('Question','TC-FLOW-01','turn3',Path(tmp)/'shots'),'Current answer')
   self.assertEqual(calls,['mobile: dragGesture'])
 def test_missing_current_copy_never_uses_previous_response_copy(self):
  with TemporaryDirectory() as tmp:
   path=self.config(tmp);cfg=json.loads(path.read_text());spec=cfg['apps']['chatgpt'];spec['capture_mode']='copy_or_text';spec['selectors']['copy_response_button']={'by':'id','value':'copy'};spec['selectors']['response_copy_relative']={'by':'id','value':'localcopy'};path.write_text(json.dumps(cfg))
   d=fake.FakeMobileDriver();reply=fake.UIElement(d,'Current rich media response');reply.find_elements=lambda by,value:[];old=d.find_elements
   d.find_elements=lambda by,value:([reply] if value.startswith('AFTER_USER:') else ([fake.UIElement(d)] if value=='copy' else old(by,value)));d.send_button.click=lambda:None
   self.assertEqual(LiveAdapter(path,'chatgpt',driver=d).send('Question','TC-MEM-01','turn2',Path(tmp)/'shots'),'Current rich media response')

 def test_sibling_xpath_scope_is_explicitly_enabled(self):
  with TemporaryDirectory() as tmp:
   p=self.config(tmp);c=json.loads(p.read_text());c['apps']['chatgpt']['uiautomator_settings']={'limitXPathContextScope':False};p.write_text(json.dumps(c))
   d=fake.FakeMobileDriver();settings=[];d.update_settings=lambda v:settings.append(v)
   LiveAdapter(p,'chatgpt',driver=d)
   self.assertEqual(settings,[{'limitXPathContextScope':False}])

 def test_xpath_literal_handles_both_quote_types(self):
  self.assertEqual(LiveAdapter._xpath_literal('Canada'),"'Canada'")
  value = chr(34)+"Canada"+chr(39)+"s capital"+chr(34)
  self.assertTrue(LiveAdapter._xpath_literal(value).startswith('concat('))
