import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake


ERROR = 'Cannot retrieve the current clipboard content: io.appium.settings clipboard.get timed out'


class ClipboardRecoveryTests(unittest.TestCase):
    def make(self, folder):
        config = fake.TestFakeAppiumAdapter()._config(folder)
        cfg = json.loads(config.read_text()); cfg['recover_clipboard_helper_once'] = True
        config.write_text(json.dumps(cfg))
        adapter = LiveAdapter(config, 'chatgpt', driver=fake.FakeMobileDriver())
        adapter._clipboard_recoveries = 0
        return adapter

    def test_only_helper_is_restarted_and_retry_is_audited(self):
        with TemporaryDirectory() as tmp:
            a = self.make(tmp); events = []
            def read():
                events.append('read')
                if len(events) == 1: raise RuntimeError(ERROR)
                return 'fresh result'
            a.driver.get_clipboard_text = read
            a.driver.terminate_app = lambda package: events.append(package)
            a._write_evidence = lambda path: events.append('evidence')
            self.assertEqual(a._read_clipboard(Path(tmp)/'turn'), 'fresh result')
            self.assertEqual(events, ['read', 'evidence', 'io.appium.settings', 'read'])
            note=json.loads((Path(tmp)/'turn.clipboard_recovery.jsonl').read_text())
            self.assertFalse(note['prompt_resent'])
            self.assertIn('timed out', note['original_error'])

    def test_unrelated_failure_never_restarts_helper(self):
        with TemporaryDirectory() as tmp:
            a = self.make(tmp)
            a.driver.get_clipboard_text = lambda: (_ for _ in ()).throw(RuntimeError('Disconnected device'))
            a.driver.terminate_app = lambda _: self.fail('unexpected restart')
            with self.assertRaisesRegex(RuntimeError, 'Disconnected'):
                a._read_clipboard(Path(tmp)/'turn')

    def test_one_recovery_limit_prevents_endless_retries(self):
        with TemporaryDirectory() as tmp:
            a = self.make(tmp); a._clipboard_recoveries = 1
            a.driver.get_clipboard_text = lambda: (_ for _ in ()).throw(RuntimeError(ERROR))
            a.driver.terminate_app = lambda _: self.fail('second restart')
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                a._read_clipboard(Path(tmp)/'turn')

    def test_second_read_failure_is_not_suppressed(self):
        with TemporaryDirectory() as tmp:
            a = self.make(tmp)
            a.driver.get_clipboard_text = lambda: (_ for _ in ()).throw(RuntimeError(ERROR))
            a.driver.terminate_app = lambda _: None
            a._write_evidence = lambda _: None
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                a._read_clipboard(Path(tmp)/'turn')
