import json
import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.live_runner import run_live
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fakes


class TestFailureEvidence(unittest.TestCase):
    def test_error_retains_screen_and_original_exception(self):
        class BrokenUI:
            def __init__(self, *args): pass
            def new_chat(self): raise RuntimeError('original UI problem')
            def close(self): pass
            def capture_error(self, folder):
                p = Path(folder); p.mkdir(parents=True, exist_ok=True)
                (p/'ERROR.png').write_bytes(b'FAKE failure screenshot')
                (p/'ERROR.xml').write_text('<failure/>')
        with TemporaryDirectory() as tmp:
            root = Path(tmp); config = root/'config.json'; config.write_text('{}')
            run_live(config, 'chatgpt', 'TC-FA-01', output=root/'run', adapter_factory=BrokenUI)
            with (root/'run/attempts.csv').open() as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row['status'], 'ERROR')
            self.assertIn('original UI problem', row['note'])
            self.assertTrue((root/'run'/row['evidence_directory']/'ERROR.png').exists())
            self.assertTrue((root/'run'/row['evidence_directory']/'ERROR.xml').exists())

    def test_error_details_retain_completed_turns_of_partial_conversation(self):
        class Interrupted:
            def __init__(self,*args):self.count=0
            def new_chat(self):pass
            def close(self):pass
            def send(self,*args):
                self.count+=1
                if self.count==2:raise RuntimeError('second turn failed')
                return 'First actual response'
        with TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.json';config.write_text('{}')
            run_live(config,'chatgpt','TC-MEM-01',output=root/'run',adapter_factory=Interrupted)
            detail=json.loads((root/'run/response_details.jsonl').read_text())
            self.assertEqual(detail['completed_turns'],1)
            self.assertEqual(detail['captured_response_groups'],[['First actual response']])

    def test_real_adapter_exposes_failure_capture(self):
        with TemporaryDirectory() as tmp:
            driver = fakes.FakeMobileDriver()
            adapter = LiveAdapter(fakes.TestFakeAppiumAdapter()._config(tmp), 'chatgpt', driver=driver)
            self.assertTrue(callable(getattr(adapter, 'capture_error', None)))
            adapter.capture_error(Path(tmp)/'error')
            self.assertTrue((Path(tmp)/'error/ERROR.png').exists())
            self.assertTrue((Path(tmp)/'error/ERROR.xml').exists())
