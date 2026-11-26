import json
import subprocess
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake


class HostPreflightTests(unittest.TestCase):
    def config(self,tmp):
        path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text())
        cfg['adb_path']='/verified/sdk/platform-tools/adb'
        cfg['apps']['chatgpt']['prelaunch_stop_host']=True
        cfg['apps']['chatgpt']['capabilities'].update({'appium:appWaitPackage':'verified.actual.host','appium:udid':'emulator-5554'})
        path.write_text(json.dumps(cfg));return path

    def test_only_inspected_distinct_host_can_be_stopped(self):
        with TemporaryDirectory() as tmp:
            path=self.config(tmp);cfg=json.loads(path.read_text());cfg['apps']['chatgpt']['capabilities'].pop('appium:appWaitPackage');path.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'host'):
                LiveAdapter(path,'chatgpt',driver=fake.FakeMobileDriver())

    def test_prelaunch_stops_host_without_clear_or_reinstall(self):
        with TemporaryDirectory() as tmp:
            a=LiveAdapter(self.config(tmp),'chatgpt',driver=fake.FakeMobileDriver())
            with patch('group7_auto.appium_adapter.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')) as call:
                a._prelaunch_host_cleanup()
            self.assertEqual(call.call_args.args[0],['/verified/sdk/platform-tools/adb','-s','emulator-5554','shell','am','force-stop','verified.actual.host'])
            self.assertTrue(a.startup_observation['host_stopped'])

    def test_failed_host_cleanup_is_not_silently_ignored(self):
        with TemporaryDirectory() as tmp:
            a=LiveAdapter(self.config(tmp),'chatgpt',driver=fake.FakeMobileDriver())
            with patch('group7_auto.appium_adapter.subprocess.run',side_effect=subprocess.CalledProcessError(1,[])):
                with self.assertRaises(subprocess.CalledProcessError):a._prelaunch_host_cleanup()
