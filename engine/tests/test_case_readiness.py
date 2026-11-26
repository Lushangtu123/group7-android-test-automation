import json
import unittest
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake
from group7_auto.live_runner import run_live
from pathlib import Path


class CaseReadinessTests(unittest.TestCase):
    def test_conversation_reset_has_case_and_group_evidence_scope(self):
        scopes=[]
        class Scoped(fake.FixtureUI):
            def prepare_conversation(self, folder, conversation):
                scopes.append((Path(folder),conversation))
        with TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json';config.write_text('{}')
            result=run_live(config,'chatgpt','TC-MEM-01,AI-NLU-06',1,Path(tmp)/'run',adapter_factory=Scoped)
            self.assertEqual(result['selected_records'],2)
            self.assertEqual([g for _,g in scopes],[1,1,2])
            self.assertTrue(all('screenshots' in folder.parts for folder,_ in scopes))

    def test_nonblocking_launch_without_inspected_ready_marker_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text())
            cfg['apps']['chatgpt']['capabilities']['appium:appWaitForLaunch']=False
            path.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'readiness'):
                LiveAdapter(path,'chatgpt',driver=fake.FakeMobileDriver())

    def test_nonblocking_launch_still_waits_for_actual_ready_ui(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text());spec=cfg['apps']['chatgpt']
            spec['capabilities']['appium:appWaitForLaunch']=False
            spec['selectors']['new_chat_ready_marker']={'by':'id','value':'ready'}
            path.write_text(json.dumps(cfg));driver=fake.FakeMobileDriver();events=[];queries=[]
            driver.new_chat_button.click=lambda:events.append('new')
            original=driver.find_elements
            def find(by,value):
                if value=='ready':
                    queries.append(value)
                    if len(queries)==1:return []
                    events.append('ready');return [fake.UIElement(driver)]
                return original(by,value)
            driver.find_elements=find
            LiveAdapter(path,'chatgpt',driver=driver).new_chat()
            self.assertEqual(events,['new','ready']);self.assertGreaterEqual(len(queries),2)

    def test_previous_unfinished_generation_is_stopped_before_new_case(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text())
            cfg['apps']['chatgpt']['selectors']['response_generating_marker']={'by':'id','value':'generating'}
            path.write_text(json.dumps(cfg));driver=fake.FakeMobileDriver();events=[]
            stop=fake.UIElement(driver);stop.click=lambda:events.append('stop_previous')
            driver.new_chat_button.click=lambda:events.append('new')
            original=driver.find_elements
            driver.find_elements=lambda by,value:([stop] if value=='generating' and 'stop_previous' not in events else ([] if value=='generating' else original(by,value)))
            LiveAdapter(path,'chatgpt',driver=driver).new_chat()
            self.assertEqual(events,['stop_previous','new'])

    def test_unstoppable_previous_generation_blocks_new_case(self):
        with TemporaryDirectory() as tmp:
            path=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(path.read_text())
            cfg['apps']['chatgpt']['selectors']['response_generating_marker']={'by':'id','value':'generating'}
            path.write_text(json.dumps(cfg));driver=fake.FakeMobileDriver();events=[]
            stop=fake.UIElement(driver);stop.click=lambda:events.append('stop_previous')
            driver.new_chat_button.click=lambda:events.append('new')
            original=driver.find_elements
            driver.find_elements=lambda by,value:[stop] if value=='generating' else original(by,value)
            a=LiveAdapter(path,'chatgpt',driver=driver);a.timeout=.003
            with self.assertRaisesRegex(TimeoutError,'Previous generation'):
                a.new_chat()
            self.assertNotIn('new',events)
