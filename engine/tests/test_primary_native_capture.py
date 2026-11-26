import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake

class PrimaryNativeCaptureTests(unittest.TestCase):
    def test_explicit_native_full_mode_never_reads_or_writes_clipboard(self):
        with TemporaryDirectory() as tmp:
            p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text());spec=cfg['apps'].pop('chatgpt');cfg['apps']['gemini']=spec
            cfg.update(atomic_response_snapshot=True,verify_prompt_text=True,input_settle_seconds=0)
            spec.update(capture_mode='native_full_response',native_full_response_capture=True)
            spec['selectors']['new_chat_ready_marker']={'by':'id','value':'ready'};p.write_text(json.dumps(cfg))
            driver=fake.FakeMobileDriver()
            driver.input_box.send_keys=lambda prompt:setattr(driver.input_box,'text',prompt)
            driver.get_clipboard_text=lambda:self.fail('Native proof must not read clipboard')
            driver.set_clipboard_text=lambda value:self.fail('Native proof must not write clipboard')
            adapter=LiveAdapter(p,'gemini',driver=driver);adapter._wait_atomic_response=lambda *a,**k:('Visible body',driver.responses[-1])
            calls=[]
            def full(prompt,prefix):calls.append(prompt);return 'Complete current response'
            adapter._capture_complete_native_response=full
            answer=adapter.send('Question','TC-FA-01','turn1',Path(tmp)/'shots')
            self.assertEqual(answer,'Complete current response');self.assertEqual(calls,['Question'])
            cap=json.loads((Path(tmp)/'shots/gemini_TC-FA-01_turn1.capture.json').read_text())
            self.assertEqual(cap['actual_mode'],'native_full_response_viewport_proof')

    def test_native_full_mode_requires_explicit_complete_proof_feature(self):
        with TemporaryDirectory() as tmp:
            p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text());cfg['apps']['chatgpt']['capture_mode']='native_full_response';p.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'complete native proof'):
                LiveAdapter(p,'chatgpt',driver=fake.FakeMobileDriver())
