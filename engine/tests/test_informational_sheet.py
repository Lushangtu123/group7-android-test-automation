import unittest
from group7_auto import informational_sheet as sheet

TITLE='Temporary chat'
BODY='This chat won’t appear in history. You can choose whether ChatGPT uses memory, files, plugins, and custom instructions to personalize replies.'

def source(body=BODY,window='9',title=TITLE,close=True,extra=''):
 return f'''<hierarchy><node package="com.openai.chatgpt" window-id="9" class="android.widget.TextView" text="{title}" heading="true"/><node package="com.openai.chatgpt" window-id="9" text="{body}"/>{'<node package="com.openai.chatgpt" window-id="'+window+'" content-desc="Close"/>' if close else ''}<node package="com.openai.chatgpt" window-id="9" text="Continue"/>{extra}</hierarchy>'''

class InformationalSheetTests(unittest.TestCase):
 def test_exact_inspected_intro_uses_close_not_continue(self):
  match=sheet.known_informational_sheet(source())
  self.assertEqual(match['action_value'],'Close')
  self.assertEqual(match['window_id'],'9')
 def test_unknown_body_is_not_acknowledged(self):
  self.assertIsNone(sheet.known_informational_sheet(source(body='Agree to terms to enable memory')))
 def test_close_in_another_window_is_not_used(self):
  self.assertIsNone(sheet.known_informational_sheet(source(window='10')))
 def test_missing_close_never_uses_continue(self):
  self.assertIsNone(sheet.known_informational_sheet(source(close=False)))
 def test_unknown_title_is_not_dismissed(self):
  self.assertIsNone(sheet.known_informational_sheet(source(title='Delete temporary chat?')))
 def test_additional_unrecognized_terms_block_dismissal(self):
  self.assertIsNone(sheet.known_informational_sheet(source(extra='<node package="com.openai.chatgpt" window-id="9" text="I accept these new terms"/>')))

class AdapterInformationalSheetTests(unittest.TestCase):
 def test_ready_lookup_dismisses_exact_intro_and_rechecks_readiness(self):
  import json
  from tempfile import TemporaryDirectory
  from group7_auto.appium_adapter import LiveAdapter
  import test_live_execution as fake
  with TemporaryDirectory() as tmp:
   config=fake.TestFakeAppiumAdapter()._config(tmp)
   cfg=json.loads(config.read_text());cfg['apps']['chatgpt']['selectors']['new_chat_ready_marker']={'by':'id','value':'ready'};config.write_text(json.dumps(cfg))
   actions=[]
   class Driver(fake.FakeMobileDriver):
    @property
    def page_source(self):return source() if not actions else '<hierarchy/>'
   d=Driver();button=fake.UIElement(d);button.click=lambda:actions.append('Close')
   ready=fake.UIElement(d)
   d.find_elements=lambda by,value:([button] if "@content-desc='Close'" in value and not actions else [ready] if value=='ready' and actions else [])
   a=LiveAdapter(config,'chatgpt',driver=d);a.timeout=.05;a.poll=.001
   self.assertIs(a._find('new_chat_ready_marker'),ready)
   self.assertEqual(actions,['Close'])
