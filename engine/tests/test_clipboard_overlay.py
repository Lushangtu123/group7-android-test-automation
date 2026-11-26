import json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake
from unittest.mock import patch

class SnapshotDriver(fake.FakeMobileDriver):
 @property
 def page_source(self):
  clip=bool(self.find_elements('id','com.android.systemui:id/clipboard_ui'))
  dismiss=bool(self.find_elements('id','com.android.systemui:id/dismiss_button'))
  return '<hierarchy>'+('<node package="com.android.systemui" resource-id="com.android.systemui:id/clipboard_ui"/>' if clip else '')+('<node package="com.android.systemui" resource-id="com.android.systemui:id/dismiss_button"/>' if dismiss else '')+'</hierarchy>'

class OverlayTests(unittest.TestCase):
 def test_atomic_overlay_read_avoids_two_different_window_query_states(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());cfg.update(manage_clipboard_overlay=True,overlay_timeout_seconds=3);path.write_text(json.dumps(cfg))
   class Clock:
    now=0
    @classmethod
    def monotonic(cls):return cls.now
    @classmethod
    def sleep(cls,value):cls.now+=value
   warm=[];closed=[]
   class Driver(SnapshotDriver):
    @property
    def page_source(self):
     warm.append(True);Clock.now=max(Clock.now,3.1)
     return super().page_source
   driver=Driver();button=fake.UIElement(driver);button.click=lambda:closed.append(True)
   def find(by,value):
    if value.endswith('/dismiss_button'):
     if not warm:Clock.now=3.1;return []
     return [button] if not closed else []
    if value.endswith('/clipboard_ui'):return [button] if not closed else []
    return []
   driver.find_elements=find;adapter=LiveAdapter(path,'chatgpt',driver=driver);adapter.poll=.75
   with patch('group7_auto.appium_adapter.time',Clock):adapter._dismiss_clipboard_overlay(expect_overlay=True)
   self.assertEqual(closed,[True])

 def test_unrelated_system_dismiss_button_is_never_clicked(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());cfg.update(manage_clipboard_overlay=True,overlay_timeout_seconds=.002);path.write_text(json.dumps(cfg))
   driver=SnapshotDriver();button=fake.UIElement(driver);clicked=[];button.click=lambda:clicked.append(True)
   driver.find_elements=lambda by,value:[button] if value.endswith('/dismiss_button') else []
   LiveAdapter(path,'chatgpt',driver=driver)._dismiss_clipboard_overlay(expect_overlay=True)
   self.assertEqual(clicked,[])
 def test_overlay_arriving_at_appearance_deadline_can_be_dismissed(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());cfg.update(manage_clipboard_overlay=True,overlay_timeout_seconds=3);path.write_text(json.dumps(cfg))
   class Clock:
    now=0
    @classmethod
    def monotonic(cls):return cls.now
    @classmethod
    def sleep(cls,seconds):cls.now+=seconds
   driver=SnapshotDriver();dismiss=fake.UIElement(driver);overlay=fake.UIElement(driver);clicked=[]
   dismiss.click=lambda:clicked.append(Clock.now)
   def find(by,value):
    if value.endswith('/dismiss_button'):return [dismiss] if Clock.now>=2.9 and not clicked else []
    if value.endswith('/clipboard_ui'):return [overlay] if Clock.now>=2.9 and (not clicked or Clock.now<clicked[0]+1) else []
    return []
   driver.find_elements=find;adapter=LiveAdapter(path,'chatgpt',driver=driver);adapter.poll=.75
   with patch('group7_auto.appium_adapter.time',Clock):adapter._dismiss_clipboard_overlay(expect_overlay=True)
   self.assertEqual(clicked,[3.0])
   self.assertLess(Clock.now,6.1)

 def test_overlay_that_remains_after_dismissal_is_still_error(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());cfg.update(manage_clipboard_overlay=True,overlay_timeout_seconds=.002);path.write_text(json.dumps(cfg))
   driver=SnapshotDriver();button=fake.UIElement(driver);driver.find_elements=lambda by,value:[button] if value.endswith(('/dismiss_button','/clipboard_ui')) else []
   adapter=LiveAdapter(path,'chatgpt',driver=driver)
   with self.assertRaisesRegex(RuntimeError,'overlay'):adapter._dismiss_clipboard_overlay(expect_overlay=True)

 def test_dismisses_actual_system_overlay_before_continuing(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);d=json.loads(path.read_text());d['manage_clipboard_overlay']=True;d['overlay_timeout_seconds']=.01;path.write_text(json.dumps(d))
   driver=SnapshotDriver();hits=[];button=fake.UIElement(driver)
   button.click=lambda:hits.append('dismissed')
   original=driver.find_elements
   driver.find_elements=lambda by,value:([button] if value in ('com.android.systemui:id/dismiss_button','com.android.systemui:id/clipboard_ui') and not hits else original(by,value))
   LiveAdapter(path,'chatgpt',driver=driver)._dismiss_clipboard_overlay(expect_overlay=True)
   self.assertEqual(hits,['dismissed'])
 def test_never_clicks_share_as_overlay_dismissal(self):
  with TemporaryDirectory() as tmp:
   path=fake.TestFakeAppiumAdapter()._config(tmp);d=json.loads(path.read_text());d['manage_clipboard_overlay']=True;d['overlay_timeout_seconds']=.003;path.write_text(json.dumps(d))
   driver=SnapshotDriver();share=fake.UIElement(driver);driver.find_elements=lambda by,value:[share] if value=='share_button' else []
   LiveAdapter(path,'chatgpt',driver=driver)._dismiss_clipboard_overlay(expect_overlay=True)
   self.assertEqual(driver.clicked,0)
