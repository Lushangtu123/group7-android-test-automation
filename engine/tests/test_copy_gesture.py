import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake


class CopyGestureTests(unittest.TestCase):
    def setup(self,tmp,copied):
        p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text());spec=cfg['apps']['chatgpt']
        spec.update(capture_mode='copy',copy_response_action='mobile: clickGesture')
        spec['selectors'].update(copy_response_button={'by':'id','value':'copy'},response_copy_relative={'by':'id','value':'localcopy'},assistant_response_after_prompt_xpath='AFTER_USER:{prompt}')
        p.write_text(json.dumps(cfg));driver=fake.FakeMobileDriver();driver.clipboard='';events=[]
        driver.get_clipboard_text=lambda:driver.clipboard;driver.set_clipboard_text=lambda value:setattr(driver,'clipboard',value)
        response=fake.UIElement(driver,'Current verified response');button=fake.UIElement(driver);button.id='CURRENT_COPY'
        button.click=lambda:self.fail('Standard native click was not the configured action')
        response.find_elements=lambda by,value:[button] if value=='localcopy' else [response]
        original=driver.find_elements;driver.find_elements=lambda by,value:[response] if value.startswith('AFTER_USER:') else original(by,value)
        driver.send_button.click=lambda:None
        def gesture(name,args):
            events.append((name,args));driver.clipboard=copied
        driver.execute_script=gesture
        return LiveAdapter(p,'chatgpt',driver=driver),events

    def test_gesture_targets_only_current_scoped_copy_element(self):
        with TemporaryDirectory() as tmp:
            a,events=self.setup(tmp,'Current verified response')
            self.assertEqual(a.send('Question','TC-FA-01','turn2',Path(tmp)/'shots'),'Current verified response')
            self.assertEqual(events,[('mobile: clickGesture',{'elementId':'CURRENT_COPY'})])

    def test_gesture_does_not_bypass_copied_text_agreement(self):
        with TemporaryDirectory() as tmp:
            a,_=self.setup(tmp,'Unrelated old response')
            with self.assertRaisesRegex(RuntimeError,'disagree'):
                a.send('Question','TC-FA-01','turn2',Path(tmp)/'shots')

    def test_unrecognized_copy_action_is_rejected(self):
        with TemporaryDirectory() as tmp:
            p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text());cfg['apps']['chatgpt']['copy_response_action']='mobile: shell';p.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'copy action'):LiveAdapter(p,'chatgpt',driver=fake.FakeMobileDriver())

    def retry_fixture(self, tmp, second_body='Current verified response', replacement='Current verified response'):
        adapter, events = self.setup(tmp, '')
        adapter.cfg['atomic_response_snapshot'] = True
        adapter.cfg['clipboard_wait_seconds'] = 0.01
        adapter.spec['selectors']['response_copy_parent_relative'] = {'by':'xpath','value':'CLICKABLE_COPY_PARENT'}
        bubble = adapter.driver.find_elements('xpath', 'AFTER_USER:Question')[0]
        parent = fake.UIElement(adapter.driver)
        parent.id = 'CURRENT_CLICKABLE_PARENT'
        parent_calls = []
        snapshots = []

        def selection(*args, **kwargs):
            snapshots.append(args[2])
            text = second_body if '.copy_retry_ready.' in args[2] else 'Current verified response'
            return text, bubble

        def click_parent():
            parent_calls.append('CURRENT_CLICKABLE_PARENT')
            adapter.driver.clipboard = replacement

        parent.click = click_parent
        original_find = bubble.find_elements
        bubble.find_elements = lambda by, value: [parent] if value == 'CLICKABLE_COPY_PARENT' else original_find(by, value)
        adapter._wait_atomic_response = selection
        adapter.driver.execute_script = lambda action, args: events.append((action, args))
        return adapter, events, parent_calls, snapshots

    def test_still_present_nonce_allows_one_same_answer_clickable_parent_retry(self):
        with TemporaryDirectory() as tmp:
            adapter, clicks, parent_clicks, snapshots = self.retry_fixture(tmp)
            shots = Path(tmp)/'shots'
            self.assertEqual(adapter.send('Question', 'TC-FA-01', 'turn1', shots),
                             'Current verified response')
            self.assertEqual(len(clicks), 1)
            self.assertEqual(parent_clicks, ['CURRENT_CLICKABLE_PARENT'])
            self.assertEqual(len(snapshots), 3)
            retry = json.loads(next(shots.glob('*.copy_action_retry.json')).read_text())
            self.assertFalse(retry['prompt_resent'])
            self.assertTrue(next(shots.glob('*_copy_nonce_unchanged.xml')).is_file())

    def test_retry_rejects_changed_observed_answer(self):
        with TemporaryDirectory() as tmp:
            adapter, _, parent_clicks, _ = self.retry_fixture(tmp, second_body='Different answer')
            with self.assertRaisesRegex(RuntimeError, 'same completed response'):
                adapter.send('Question', 'TC-FA-01', 'turn1', Path(tmp)/'shots')
            self.assertEqual(parent_clicks, [])

    def test_wrong_fresh_text_after_retry_still_errors(self):
        with TemporaryDirectory() as tmp:
            adapter, _, parent_clicks, _ = self.retry_fixture(tmp, replacement='Unrelated text')
            with self.assertRaisesRegex(RuntimeError, 'disagree'):
                adapter.send('Question', 'TC-FA-01', 'turn1', Path(tmp)/'shots')
            self.assertEqual(len(parent_clicks), 1)
