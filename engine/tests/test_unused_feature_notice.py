import json
import unittest
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake

TITLE='Creating content from images and files'

class NoticeTests(unittest.TestCase):
    def setup(self,tmp,title=TITLE,has_cancel=True):
        path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());spec=cfg['apps']['chatgpt']
        spec['selectors']['new_chat_menu_button']={'by':'id','value':'menu'}
        spec['startup_notice_cancel']={'title_resource_id':'verified.host:id/notice_title','title_text':TITLE,'cancel_resource_id':'android:id/button2','cancel_text':'Cancel'}
        path.write_text(json.dumps(cfg));events=[]
        class Driver(fake.FakeMobileDriver):
            visible=True
            @property
            def page_source(self):
                if not self.visible:return '<hierarchy/>'
                return '<hierarchy><node package="verified.host" window-id="42" resource-id="verified.host:id/notice_title" text="'+title+'"/>'+('<node package="verified.host" window-id="42" resource-id="android:id/button2" text="Cancel"/>' if has_cancel else '')+'<node package="verified.host" window-id="42" resource-id="android:id/button1" text="Agree"/></hierarchy>'
        driver=Driver();cancel=fake.UIElement(driver);menu=fake.UIElement(driver)
        def clicked_cancel():driver.visible=False;events.append('cancel')
        cancel.click=clicked_cancel;menu.click=lambda:events.append('menu')
        driver.new_chat_button.click=lambda:events.append('new')
        original=driver.find_elements
        def find(by,value):
            if value=='menu':return [menu] if not driver.visible else []
            if 'android:id/button2' in value:return [cancel] if has_cancel and driver.visible else []
            if 'android:id/button1' in value:self.fail('Agree must never be located')
            return original(by,value)
        driver.find_elements=find
        a=LiveAdapter(path,'chatgpt',driver=driver);a.timeout=.01
        return a,events

    def test_only_known_unused_feature_notice_is_cancelled_before_menu(self):
        with TemporaryDirectory() as tmp:
            a,events=self.setup(tmp);a.new_chat()
            self.assertEqual(events,['cancel','menu','new'])
            self.assertTrue(a.last_reset_observation['startup_notice_cancelled'])

    def test_unrelated_cancel_dialog_is_left_for_explicit_handling(self):
        with TemporaryDirectory() as tmp:
            a,events=self.setup(tmp,title='Discard conversation?')
            with self.assertRaises(TimeoutError):a.new_chat()
            self.assertEqual(events,[])

    def test_no_cancellation_control_never_falls_back_to_agree(self):
        with TemporaryDirectory() as tmp:
            a,events=self.setup(tmp,has_cancel=False)
            with self.assertRaisesRegex(RuntimeError,'cancellation'):a.new_chat()
            self.assertEqual(events,[])
