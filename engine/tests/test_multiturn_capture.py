import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fakes


class TestMultiturnCapture(unittest.TestCase):
    def test_optional_temporary_chat_step(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg=json.loads(config.read_text())
            cfg['apps']['chatgpt']['selectors']['new_chat_final_button']={'by':'id','value':'temporary'}
            cfg['apps']['chatgpt']['selectors']['new_chat_ready_marker']={'by':'id','value':'isolated'}
            config.write_text(json.dumps(cfg))
            driver=fakes.FakeMobileDriver();actions=[]
            driver.new_chat_button.click=lambda:actions.append('new')
            temporary=fakes.UIElement(driver);temporary.click=lambda:actions.append('temporary')
            original=driver.find_elements
            def find(kind,value):
                if value=='temporary':return [temporary]
                if value=='isolated':
                    actions.append('verified')
                    return [temporary]
                return original(kind,value)
            driver.find_elements=find
            LiveAdapter(config,'chatgpt',driver=driver).new_chat()
            self.assertEqual(actions,['new','temporary','verified'])

    def test_input_is_reacquired_after_focus_replaces_it(self):
        with TemporaryDirectory() as tmp:
            driver=fakes.FakeMobileDriver();old=driver.input_box
            replacement=fakes.UIElement(driver)
            def focus():
                driver.input_box=replacement
            old.click=focus
            def stale(text):raise RuntimeError('stale focused input')
            old.send_keys=stale
            answer=LiveAdapter(fakes.TestFakeAppiumAdapter()._config(tmp),'chatgpt',driver=driver).send('Question','TC-FA-01','turn1',Path(tmp)/'shots')
            self.assertEqual(answer,'The capital is Ottawa.')

    def test_never_sends_if_prompt_text_was_not_entered(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(config.read_text())
            cfg['verify_prompt_text']=True;cfg['prompt_verify_seconds']=0.005;config.write_text(json.dumps(cfg))
            driver=fakes.FakeMobileDriver();actions=[];driver.send_button.click=lambda:actions.append('send')
            with self.assertRaisesRegex(RuntimeError,'Typed prompt'):
                LiveAdapter(config,'chatgpt',driver=driver).send('Expected actual prompt','TC-FA-01','turn1',Path(tmp)/'shots')
            self.assertEqual(actions,[])

    def test_verified_prompt_is_sent(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(config.read_text())
            cfg['verify_prompt_text']=True;cfg['input_settle_seconds']=0;config.write_text(json.dumps(cfg))
            driver=fakes.FakeMobileDriver()
            driver.input_box.send_keys=lambda text:setattr(driver.input_box,'text',text)
            answer=LiveAdapter(config,'chatgpt',driver=driver).send('Actual prompt','TC-FA-01','turn1',Path(tmp)/'shots')
            self.assertEqual(answer,'The capital is Ottawa.')

    def test_recycled_messages_can_have_same_count(self):
        with TemporaryDirectory() as tmp:
            driver = fakes.FakeMobileDriver()
            driver.send_button.click = lambda: setattr(driver, 'responses', [fakes.UIElement(driver, 'Fresh answer: Ottawa.')])
            adapter = LiveAdapter(fakes.TestFakeAppiumAdapter()._config(tmp), 'chatgpt', driver=driver)
            self.assertEqual(adapter.send('Question', 'TC-FA-01', 'turn2', Path(tmp)/'shots'), 'Fresh answer: Ottawa.')

    def test_scrolls_to_response_footer(self):
        with TemporaryDirectory() as tmp:
            config = fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg = json.loads(config.read_text())
            cfg['apps']['chatgpt']['selectors']['response_scroll_container'] = {'by':'id','value':'scroll'}
            config.write_text(json.dumps(cfg))
            driver = fakes.FakeMobileDriver()
            driver.responses = []
            driver.send_button.click = lambda: None
            scroll = fakes.UIElement(driver); scroll.id = 'scroll-id'
            original = driver.find_elements
            driver.find_elements = lambda kind,value: [scroll] if value=='scroll' else original(kind,value)
            calls = []
            def execute(name, args):
                calls.append((name,args))
                driver.responses = [fakes.UIElement(driver, 'Scrolled answer: Ottawa.')]
                return False
            driver.execute_script = execute
            adapter = LiveAdapter(config, 'chatgpt', driver=driver)
            self.assertEqual(adapter.send('Question', 'TC-FA-01', 'turn1', Path(tmp)/'shots'), 'Scrolled answer: Ottawa.')
            self.assertEqual(calls[0][0], 'mobile: scrollGesture')

    def test_footer_below_input_is_scrolled_before_accepting_completion(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg=json.loads(config.read_text());spec=cfg['apps']['chatgpt'];spec['response_footer_max_y']=2100
            spec['selectors']['response_finished_marker']={'by':'id','value':'footer'}
            spec['selectors']['response_scroll_container']={'by':'id','value':'scroll'}
            config.write_text(json.dumps(cfg));driver=fakes.FakeMobileDriver();actions=[]
            footer=fakes.UIElement(driver);footer.rect={'y':2289,'height':95}
            scroll=fakes.UIElement(driver);scroll.id='scroll'
            original=driver.find_elements
            driver.find_elements=lambda kind,value:([footer] if value=='footer' else ([scroll] if value=='scroll' else original(kind,value)))
            def execute(name,args):
                actions.append('scrolled');footer.rect={'y':1800,'height':95}
            driver.execute_script=execute
            LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-FA-03','turn1',Path(tmp)/'shots')
            self.assertEqual(actions,['scrolled'])

    def test_does_not_scroll_or_finish_while_generation_marker_is_visible(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(config.read_text())
            spec=cfg['apps']['chatgpt'];spec['selectors']['response_generating_marker']={'by':'id','value':'generating'}
            spec['selectors']['response_scroll_container']={'by':'id','value':'scroll'}
            config.write_text(json.dumps(cfg));driver=fakes.FakeMobileDriver();checks=[]
            marker=fakes.UIElement(driver);scroll=fakes.UIElement(driver);scroll.id='scroll'
            original=driver.find_elements
            def find(kind,value):
                if value=='generating':
                    checks.append('checked')
                    return [marker] if len(checks)<=3 else []
                if value=='scroll':return [scroll]
                return original(kind,value)
            driver.find_elements=find
            driver.execute_script=lambda *args:self.fail('Must not scroll during generation')
            LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-MEM-02','turn3',Path(tmp)/'shots')
            self.assertGreaterEqual(len(checks),4)

    def test_copy_mode_preserves_markdown_code(self):
        with TemporaryDirectory() as tmp:
            config = fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg = json.loads(config.read_text());cfg['apps']['chatgpt']['capture_mode']='copy'
            cfg['apps']['chatgpt']['selectors']['copy_response_button']={'by':'id','value':'copy'}
            config.write_text(json.dumps(cfg))
            driver = fakes.FakeMobileDriver()
            full = 'Here is the code:\n```python\nprint("Hello")\n```'
            driver.clipboard = 'previous clipboard'
            driver.get_clipboard_text = lambda: driver.clipboard
            driver.set_clipboard_text = lambda text: setattr(driver,'clipboard',text)
            copy = fakes.UIElement(driver)
            copy.click = lambda: setattr(driver,'clipboard',full)
            original = driver.find_elements
            driver.find_elements = lambda kind,value: [copy] if value=='copy' else original(kind,value)
            driver.send_button.click = lambda: driver.responses.append(fakes.UIElement(driver, 'Here is the code:\nprint("Hello")'))
            adapter = LiveAdapter(config,'chatgpt',driver=driver)
            self.assertEqual(adapter.send('Code','TC-FLOW-01','turn3',Path(tmp)/'shots'),full)
            audit=json.loads((Path(tmp)/'shots/chatgpt_TC-FLOW-01_turn3.clipboard_observation.json').read_text())
            self.assertEqual(audit['copied_text'],full)

    def test_copy_menu_is_opened_before_copy(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg=json.loads(config.read_text());cfg['apps']['chatgpt']['capture_mode']='copy'
            cfg['apps']['chatgpt']['selectors']['copy_response_button']={'by':'id','value':'copy'}
            cfg['apps']['chatgpt']['selectors']['response_actions_button']={'by':'id','value':'menu'}
            config.write_text(json.dumps(cfg));driver=fakes.FakeMobileDriver();actions=[]
            driver.clipboard='';driver.get_clipboard_text=lambda:driver.clipboard
            driver.set_clipboard_text=lambda text:setattr(driver,'clipboard',text)
            menu=fakes.UIElement(driver);menu.click=lambda:actions.append('menu')
            copy=fakes.UIElement(driver)
            def copied():
                self.assertEqual(actions,['menu'])
                driver.clipboard='The capital is Ottawa.'
            copy.click=copied;original=driver.find_elements
            driver.find_elements=lambda kind,value:[menu] if value=='menu' else ([copy] if value=='copy' else original(kind,value))
            LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-FA-01','turn1',Path(tmp)/'shots')

    def test_explicit_copy_or_text_records_unavailable_copy(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg=json.loads(config.read_text());cfg['apps']['chatgpt']['capture_mode']='copy_or_text'
            cfg['apps']['chatgpt']['selectors']['copy_response_button']={'by':'id','value':'absent-copy'}
            config.write_text(json.dumps(cfg));driver=fakes.FakeMobileDriver()
            answer=LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-FA-01','turn1',Path(tmp)/'shots')
            self.assertEqual(answer,'The capital is Ottawa.')
            metadata=json.loads((Path(tmp)/'shots/chatgpt_TC-FA-01_turn1.capture.json').read_text())
            self.assertEqual(metadata['actual_mode'],'native_text_copy_unavailable')

    def test_required_complete_copy_never_accepts_unverified_native_fragment(self):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg=json.loads(config.read_text());spec=cfg['apps']['chatgpt']
            spec['capture_mode']='copy_or_text';spec['require_full_response_copy']=True
            spec['selectors']['copy_response_button']={'by':'id','value':'absent-copy'}
            config.write_text(json.dumps(cfg));driver=fakes.FakeMobileDriver()
            with self.assertRaisesRegex(RuntimeError,'native fallback coverage unverified'):
                LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-FA-01','turn1',Path(tmp)/'shots')

    def _copy_variant(self,visible,copied):
        with TemporaryDirectory() as tmp:
            config=fakes.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(config.read_text())
            cfg['apps']['chatgpt']['capture_mode']='copy';cfg['apps']['chatgpt']['selectors']['copy_response_button']={'by':'id','value':'copy'}
            config.write_text(json.dumps(cfg));driver=fakes.FakeMobileDriver();driver.clipboard=''
            driver.get_clipboard_text=lambda:driver.clipboard
            driver.set_clipboard_text=lambda text:setattr(driver,'clipboard',text)
            button=fakes.UIElement(driver);button.click=lambda:setattr(driver,'clipboard',copied)
            original=driver.find_elements;driver.find_elements=lambda kind,value:[button] if value=='copy' else original(kind,value)
            driver.send_button.click=lambda:driver.responses.append(fakes.UIElement(driver,visible))
            return LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-FA-03','turn1',Path(tmp)/'shots')

    def test_markdown_escaped_numbering_matches_visible_text(self):
        copied=r'4\. A new city was designed to become the national capital.'
        self.assertEqual(self._copy_variant('4. A new city was designed to become the national capital.',copied),copied)

    def test_copy_content_disagreement_still_errors(self):
        with self.assertRaisesRegex(RuntimeError,'disagree'):
            self._copy_variant('The capital of Canada is Ottawa.','The capital of Canada is Toronto.')

    def test_copy_never_accepts_unchanged_clipboard(self):
        with TemporaryDirectory() as tmp:
            config = fakes.TestFakeAppiumAdapter()._config(tmp)
            cfg = json.loads(config.read_text());cfg['clipboard_wait_seconds']=0.005
            cfg['apps']['chatgpt']['capture_mode']='copy'
            cfg['apps']['chatgpt']['selectors']['copy_response_button']={'by':'id','value':'copy'}
            config.write_text(json.dumps(cfg))
            driver = fakes.FakeMobileDriver();driver.clipboard='The capital is Ottawa.'
            driver.get_clipboard_text=lambda:driver.clipboard
            driver.set_clipboard_text=lambda text:setattr(driver,'clipboard',text)
            copy=fakes.UIElement(driver)
            original=driver.find_elements
            driver.find_elements=lambda kind,value:[copy] if value=='copy' else original(kind,value)
            with self.assertRaises(RuntimeError):
                LiveAdapter(config,'chatgpt',driver=driver).send('Question','TC-FA-01','turn1',Path(tmp)/'shots')
