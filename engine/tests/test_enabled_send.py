import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake


class EnabledSendTests(unittest.TestCase):
    def fixture(self, folder, *, enabled=False, enable_after_reentry=True):
        driver = fake.FakeMobileDriver()
        driver.input_box.text = 'Exact prompt'
        adapter = LiveAdapter(fake.TestFakeAppiumAdapter()._config(folder), 'chatgpt', driver=driver)
        adapter.spec['selectors']['enabled_send_control'] = {'by':'xpath','value':'enabled'}
        adapter.spec['selectors']['disabled_send_control'] = {'by':'xpath','value':'disabled'}
        adapter.cfg['send_control_reentry_after_seconds'] = 0.002
        adapter.cfg['prompt_verify_seconds'] = 0.012
        adapter._write_evidence = lambda *args, **kwargs: None
        sent_events = []
        state = {'enabled': enabled}
        original_find = driver.find_elements
        def find(by, value):
            if value == 'enabled':
                return [driver.send_button] if state['enabled'] else []
            if value == 'disabled':
                return [] if state['enabled'] else [driver.send_button]
            return original_find(by, value)

        driver.find_elements = find

        def clear():
            sent_events.append('CLEAR_UNSENT_INPUT')
            driver.input_box.text = ''

        def type_text(action, args):
            sent_events.append((action, args))
            driver.input_box.text = args['text']
            state['enabled'] = enable_after_reentry

        driver.input_box.clear = clear
        driver.execute_script = type_text
        return adapter, sent_events

    def test_enabled_control_does_not_reenter_prompt(self):
        with TemporaryDirectory() as folder:
            adapter, events = self.fixture(folder, enabled=True)
            ready = adapter._await_enabled_send_control('Exact prompt', Path(folder)/'turn')
            self.assertIs(ready, adapter.driver.send_button)
            self.assertEqual(events, [])

    def test_disabled_control_reenters_exact_unsent_text_once(self):
        with TemporaryDirectory() as folder:
            adapter, events = self.fixture(folder)
            ready = adapter._await_enabled_send_control('Exact prompt', Path(folder)/'turn')
            self.assertIs(ready, adapter.driver.send_button)
            self.assertEqual(events, ['CLEAR_UNSENT_INPUT', ('mobile: type', {'text':'Exact prompt'})])
            self.assertTrue((Path(folder)/'turn.send_control_recovery.json').is_file())
            self.assertEqual(adapter.driver.clicked, 0, 'Readiness never dispatches the prompt')

    def test_persistent_disabled_control_raises_before_sending(self):
        with TemporaryDirectory() as folder:
            adapter, events = self.fixture(folder, enable_after_reentry=False)
            with self.assertRaisesRegex(TimeoutError, 'disabled'):
                adapter._await_enabled_send_control('Exact prompt', Path(folder)/'turn')
            self.assertEqual(events.count('CLEAR_UNSENT_INPUT'), 1)
            self.assertEqual(adapter.driver.clicked, 0)

    def test_input_change_blocks_submission_even_if_control_enabled(self):
        with TemporaryDirectory() as folder:
            adapter, events = self.fixture(folder, enabled=True)
            adapter.driver.input_box.text = 'Different text'
            with self.assertRaisesRegex(RuntimeError, 'Exact prompt'):
                adapter._await_enabled_send_control('Exact prompt', Path(folder)/'turn')
            self.assertEqual(events, [])
