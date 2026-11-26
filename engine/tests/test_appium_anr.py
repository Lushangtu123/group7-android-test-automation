import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from group7_auto.appium_adapter import LiveAdapter
from group7_auto.android_snapshot import appium_settings_anr
import test_live_execution as fake


ANR = """<hierarchy><node package="android" window-id="8">
<node package="android" window-id="8" resource-id="android:id/alertTitle" text="Appium Settings isn't responding"/>
<node package="android" window-id="8" resource-id="android:id/aerr_close" text="Close app"/>
</node></hierarchy>"""


class AppiumAnrTests(unittest.TestCase):
    def test_only_exact_helper_dialog_matches(self):
        self.assertTrue(appium_settings_anr(ANR))
        self.assertFalse(appium_settings_anr(ANR.replace("Appium Settings", "ChatGPT")))
        self.assertFalse(appium_settings_anr(ANR.replace('id/aerr_close', 'id/other')))
        self.assertFalse(appium_settings_anr(ANR.replace('window-id="8" resource-id="android:id/aerr_close"', 'window-id="9" resource-id="android:id/aerr_close"')))

    def test_helper_dialog_is_diagnosed_before_any_scroll(self):
        with TemporaryDirectory() as tmp:
            config = fake.TestFakeAppiumAdapter()._config(tmp)

            class BlockedDriver(fake.FakeMobileDriver):
                @property
                def page_source(self):
                    return ANR

            adapter = LiveAdapter(config, 'chatgpt', driver=BlockedDriver())
            with self.assertRaisesRegex(RuntimeError, 'Appium Settings ANR'):
                adapter._wait_atomic_response('Question', 0, Path(tmp) / 'state.jsonl')

    def test_recovery_is_scoped_to_helper_and_preserves_original_observation(self):
        with TemporaryDirectory() as tmp:
            config = fake.TestFakeAppiumAdapter()._config(tmp)
            cfg = json.loads(config.read_text())
            cfg['recover_appium_settings_anr_at_case_boundary'] = True
            config.write_text(json.dumps(cfg))
            calls = []

            class RecoveringDriver(fake.FakeMobileDriver):
                @property
                def page_source(self):
                    return ANR if not calls else '<hierarchy/>'

                def terminate_app(self, package):
                    calls.append(package)

            adapter = LiveAdapter(config, 'chatgpt', driver=RecoveringDriver())
            prefix = Path(tmp) / 'start'
            adapter._recover_appium_settings_anr(prefix)
            self.assertEqual(calls, ['io.appium.settings'])
            self.assertIn('Appium Settings', (Path(tmp) / 'start_helper_anr.xml').read_text())
            self.assertFalse(json.loads((Path(tmp) / 'start.helper_anr_recovery.json').read_text())['prompt_resent'])
