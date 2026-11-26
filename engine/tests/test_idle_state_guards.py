import json
import unittest
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake


class IdleStateGuardTests(unittest.TestCase):
    def test_reduced_native_idle_wait_requires_explicit_state_validation(self):
        with TemporaryDirectory() as tmp:
            p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text())
            cfg['apps']['chatgpt']['uiautomator_settings']={'waitForIdleTimeout':1000}
            p.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'state validation'):
                LiveAdapter(p,'chatgpt',driver=fake.FakeMobileDriver())

    def test_reduced_idle_wait_keeps_atomic_prompt_and_ready_guards(self):
        with TemporaryDirectory() as tmp:
            p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text())
            cfg.update(atomic_response_snapshot=True,verify_prompt_text=True)
            cfg['apps']['chatgpt']['uiautomator_settings']={'waitForIdleTimeout':1000}
            cfg['apps']['chatgpt']['selectors']['new_chat_ready_marker']={'by':'id','value':'ready'}
            p.write_text(json.dumps(cfg));driver=fake.FakeMobileDriver();settings=[]
            driver.update_settings=lambda value:settings.append(value)
            a=LiveAdapter(p,'chatgpt',driver=driver)
            self.assertTrue(a.cfg['atomic_response_snapshot'])
            self.assertTrue(a.cfg['verify_prompt_text'])
            self.assertEqual(settings,[{'waitForIdleTimeout':1000}])
