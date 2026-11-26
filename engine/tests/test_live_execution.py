import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from group7_auto.live_runner import run_live
from group7_auto.fixture import T
from group7_auto.appium_adapter import LiveAdapter
from group7_auto.costs import reported_costs, make_worklog, evaluate_worklog

class FixtureUI:
    """Only a synthetic MOCK; never claims to drive Android."""
    fail_turn=None
    def __init__(self, config_path, app):
        self.app=app
        self.case=None
        self.index=0
        self.conv_counter=0
    def new_chat(self):
        self.index=0
        self.conv_counter+=1
    def send(self,prompt,case_id,turn_idx,output):
        if self.fail_turn and (case_id,self.index+1)==self.fail_turn:
            raise RuntimeError('simulated UI timeout')
        if self.case!=case_id:
            self.case=case_id
            self.index=0
            self.conv_counter=1
        values=T[case_id]
        groups=values if isinstance(values[0],list) else [values]
        group_idx=self.conv_counter-1 if len(groups)>1 else 0
        out=groups[group_idx][self.index]
        self.index+=1
        return out
    def close(self):pass


class TestLiveExecution(unittest.TestCase):
    def test_all_19_cases_twice_each_app(self):
        with TemporaryDirectory() as tmp:
            cfg=Path(tmp)/'config.json';cfg.write_text('{}')
            d=Path(tmp)/'attempts'
            result=run_live(str(cfg),which='both',repeats=2,output=d,adapter_factory=FixtureUI)
            self.assertEqual(result['planned_app_case_repetitions'],76)
            self.assertEqual(result['selected_records'],76)
            self.assertEqual(result['status_counts'].get('PASS'),68)
            self.assertEqual(result['status_counts'].get('REVIEW'),8)
            self.assertEqual(result['status_counts'].get('ERROR',0),0)
            with (d/'attempts.csv').open() as f:self.assertEqual(len(list(csv.DictReader(f))),76)
            # Same folder, rerun with resume does not duplicate data.
            again=run_live(str(cfg),which='both',repeats=2,output=d,resume=True,adapter_factory=FixtureUI)
            self.assertEqual(again['all_checkpointed_attempts'],76)
    def test_exception_preserves_completed_turns_and_rerun(self):
        class FailingUI(FixtureUI):fail_turn=('AI-MEM-04',3)
        with TemporaryDirectory() as tmp:
            cfg=Path(tmp)/'config.json';cfg.write_text('{}')
            d=Path(tmp)/'live'
            a=run_live(str(cfg),'chatgpt','AI-MEM-04',1,d,adapter_factory=FailingUI)
            self.assertEqual(a['status_counts'].get('ERROR'),1)
            with (d/'attempts.csv').open(encoding='utf-8') as fh:
                r=list(csv.DictReader(fh))[0]
            self.assertEqual(int(r['completed_turns']),2)
            self.assertEqual(len((d/'turn_checkpoints.jsonl').read_text().splitlines()),2)
            b=run_live(str(cfg),'chatgpt','AI-MEM-04',1,d,resume=True,rerun_errors=True,adapter_factory=FixtureUI)
            self.assertEqual(b['status_counts'].get('PASS'),1)
            self.assertEqual(b['all_checkpointed_attempts'],2)
    def test_startup_error_is_recorded(self):
        def fail(config,app):raise RuntimeError('device offline')
        with TemporaryDirectory() as tmp:
            cfg=Path(tmp)/'config.json';cfg.write_text('{}')
            s=run_live(str(cfg),'gemini','TC-FA-01',output=Path(tmp)/'evidence',adapter_factory=fail)
            self.assertEqual(s['status_counts']['ERROR'],1)
    def test_config_blocks_guesswork(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'c.json';p.write_text(json.dumps({'apps':{'gemini':{
               'platform':'Android','capabilities':{'platformName':'Android',
               'appium:automationName':'UiAutomator2','appium:appPackage':'REPLACE_WITH_VERIFIED'},
               'selectors':{k:{'by':'id','value':'foo'} for k in
                  ('new_chat_button','prompt_input','send_button','assistant_response_bubbles')}}}}))
            with self.assertRaises(ValueError):LiveAdapter(str(p),'gemini',driver=object())
    def test_costs_do_not_invent_labor(self):
        with TemporaryDirectory() as tmp:
            p=make_worklog(Path(tmp)/'time.csv')
            labor=evaluate_worklog(p)
            self.assertIsNone(labor['person_minutes_total_if_complete'])
            c=reported_costs(p)
            self.assertAlmostEqual(c['superseded_checkpointed_duration_s'],651.0615)
            self.assertEqual(c['financial_automation_cost'],'NOT MEASURED')

if __name__=='__main__':unittest.main()

class UIElement:
    def __init__(self,driver,text=''):
        self.driver=driver
        self.text=text
    def click(self):
        self.driver.clicked+=1
        if self is self.driver.send_button: self.driver.responses.append(UIElement(self.driver,'The capital is Ottawa.'))
    def send_keys(self,prompt):self.driver.entered.append(prompt)
    def find_elements(self,kind,value):return [self]

class FakeMobileDriver:
    def __init__(self,emit_new_response=True):
        self.entered=[];self.clicked=0
        self.responses=[UIElement(self,'Earlier answer.')]
        self.input_box=UIElement(self)
        self.send_button=UIElement(self)
        self.new_chat_button=UIElement(self)
        self.emit_new_response=emit_new_response
    def find_elements(self,kind,value):
        if value=='response':return self.responses
        if value=='send':return [self.send_button] if self.emit_new_response else [self.input_box]
        if value=='input':return [self.input_box]
        if value=='new':return [self.new_chat_button]
        return []
    def save_screenshot(self,output):Path(output).write_bytes(b'FAKE_SCREENSHOT')
    @property
    def page_source(self):return '<view>FAKE XML for testing only</view>'
    def quit(self):pass

class TestFakeAppiumAdapter(unittest.TestCase):
    def _config(self,folder):
        cfg={'timeout_seconds':0.025,'stable_seconds':0.001,'poll_seconds':0.001,
             'chat_reset_wait_seconds':0.001,
             'apps':{'chatgpt':{'platform':'Android','capture_mode':'text',
               'capabilities':{'platformName':'Android','appium:automationName':'UiAutomator2',
                                'appium:appPackage':'example.test.app'},
               'selectors':{'new_chat_button':{'by':'id','value':'new'},
                 'prompt_input':{'by':'id','value':'input'},
                 'send_button':{'by':'id','value':'send'},
                 'assistant_response_bubbles':{'by':'id','value':'response'}}}}}
        f=Path(folder)/'fake.json'; f.write_text(json.dumps(cfg));return f
    def test_fresh_response_evidence(self):
        with TemporaryDirectory() as t:
            d=FakeMobileDriver()
            a=LiveAdapter(self._config(t),'chatgpt',driver=d)
            got=a.send('What is the capital of Canada?','TC-FA-01','1_1',Path(t)/'shots')
            self.assertEqual(got,'The capital is Ottawa.')
            self.assertTrue((Path(t)/'shots'/'chatgpt_TC-FA-01_1_1.png').exists())
            self.assertTrue((Path(t)/'shots'/'chatgpt_TC-FA-01_1_1.xml').exists())
            self.assertEqual(d.entered,['What is the capital of Canada?'])
    def test_refuses_stale_response(self):
        class StaleDriver(FakeMobileDriver):
            def __init__(self):super().__init__()
            def find_elements(self,kind,value):
                if value=='response':return [self.responses[0]]
                return super().find_elements(kind,value)
        with TemporaryDirectory() as t:
            a=LiveAdapter(self._config(t),'chatgpt',driver=StaleDriver())
            with self.assertRaises(TimeoutError):
                a.send('Question','TC-FA-01','1_1',Path(t)/'shots')
