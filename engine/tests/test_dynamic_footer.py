import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
from unittest.mock import patch
import test_live_execution as fake


def snapshot(copy_bounds):
    # Minimized from r4/Gemini TC-MEM-02 ERROR.xml: the quota banner
    # raises the fixed input half-sheet to1853, covering the Copy button.
    return f'''<hierarchy><node resource-id="assistant_robin_user_message_text" text="Question"/>
    <node resource-id="assistant_robin_content_message_container"><node resource-id="assistant_robin_text" text="Current answer"/></node>
    <node><node resource-id="assistant_robin_message_content_actions_options_button"/>
    <node content-desc="Copy" bounds="{copy_bounds}"/></node>
    <node resource-id="assistant_robin_chat_input_half_sheet" bounds="[53,1853][1027,2305]" displayed="true"/>
    </hierarchy>'''


class DynamicFooterTests(unittest.TestCase):
    def test_same_text_with_moving_footer_is_not_yet_stable(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());cfg['apps']['gemini']=cfg['apps'].pop('chatgpt');path.write_text(json.dumps(cfg))
            class Clock:
                now=0
                @classmethod
                def monotonic(cls):return cls.now
                @classmethod
                def sleep(cls,value):cls.now+=value
            class Driver:
                @property
                def page_source(self):return snapshot('[405,1500][531,1626]' if Clock.now<2.5 else '[405,1300][531,1426]')
            a=LiveAdapter(path,'gemini',driver=Driver());a.timeout=20;a.stable=3;a.poll=.5;a._turn_bubbles=lambda *_:([object()],True)
            with patch('group7_auto.appium_adapter.time',Clock):a._wait_atomic_response('Question',0,Path(tmp)/'state.jsonl')
            self.assertGreaterEqual(Clock.now,5.5)

    def test_copy_behind_actual_input_sheet_is_scrolled_before_acceptance(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text())
            cfg['apps']['gemini']=cfg['apps'].pop('chatgpt');path.write_text(json.dumps(cfg))
            driver=SimpleNamespace();driver.page_source=snapshot('[405,1859][531,1985]');calls=[]
            def scroll(name,args):
                calls.append(name);driver.page_source=snapshot('[405,1500][531,1626]')
            driver.execute_script=scroll
            adapter=LiveAdapter(path,'gemini',driver=driver)
            adapter._turn_bubbles=lambda prompt,before:([object()],True)
            result=adapter._wait_atomic_response('Question',0,Path(tmp)/'state.jsonl')
            self.assertEqual(result[0],'Current answer')
            self.assertEqual(calls,['mobile: swipeGesture'])

    def test_visible_copy_above_actual_input_sheet_needs_no_scroll(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text())
            cfg['apps']['gemini']=cfg['apps'].pop('chatgpt');path.write_text(json.dumps(cfg))
            driver=SimpleNamespace();driver.page_source=snapshot('[405,1500][531,1626]')
            driver.execute_script=lambda *_: self.fail('unnecessary scroll')
            adapter=LiveAdapter(path,'gemini',driver=driver);adapter._turn_bubbles=lambda *_:([object()],True)
            self.assertEqual(adapter._wait_atomic_response('Question',0,Path(tmp)/'state.jsonl')[0],'Current answer')
