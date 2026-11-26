import json
import tempfile
import unittest
from pathlib import Path
from mac_tools.config_validator import validate_config
from mac_tools.make_local_config import make_config, ROOT
from mac_tools.summarize_live import summarize


class TestMacHelpers(unittest.TestCase):
    def test_template_must_not_pass(self):
        errors = validate_config(ROOT/'data'/'android_appium_config.example.json', device_check=False)
        self.assertTrue(errors)
        self.assertTrue(any('appium:appPackage' in x for x in errors))

    def test_make_local_keeps_ui_placeholders(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'local.json'
            make_config('emulator-5554','inspected.chatgpt','inspected.gemini',target)
            payload=json.loads(target.read_text())
            self.assertEqual(payload['apps']['chatgpt']['capabilities']['appium:udid'],'emulator-5554')
            self.assertTrue(validate_config(target,device_check=False))
            with self.assertRaises(FileExistsError):make_config('emulator-5554',dest=target)

    def test_summary_preserves_review_and_error(self):
        with tempfile.TemporaryDirectory() as d:
            import csv
            folder=Path(d)
            fields=['application','case_id','repeat','status','duration_seconds']
            rows=[
                dict(application='chatgpt',case_id='A',repeat='1',status='ERROR',duration_seconds='3'),
                dict(application='chatgpt',case_id='A',repeat='1',status='PASS',duration_seconds='4'),
                dict(application='gemini',case_id='A',repeat='1',status='REVIEW',duration_seconds='5'),
            ]
            (folder/'summary.json').write_text(json.dumps({'run_type':'LIVE_APPIUM_UI','evidence_source':'THIS_RUN_ONLY'}))
            with (folder/'attempts.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
            s=summarize(folder)
            self.assertEqual(s['all_checkpointed_attempts'],3)
            self.assertEqual(s['counts']['PASS'],1)
            self.assertEqual(s['counts']['REVIEW'],1)
            self.assertEqual(s['counts']['ERROR'],0)
            self.assertEqual(s['selected_latest_app_case_repeat_records'],2)

if __name__=='__main__':unittest.main()
