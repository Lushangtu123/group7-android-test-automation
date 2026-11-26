import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from group7_auto.catalog import load_cases
from group7_auto.oracles import evaluate
from group7_auto.appium_adapter import LiveAdapter
from group7_auto.live_runner import run_live
import test_live_execution as live_fakes

FakeMobileDriver = live_fakes.FakeMobileDriver
UIElement = live_fakes.UIElement


class TestOracleRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c.case_id: c for c in load_cases()}

    def verdict(self, case_id, answer):
        case = self.cases[case_id]
        groups = [['OK'] * len(group) for group in case.conversations]
        groups[-1][-1] = answer
        return evaluate(case, groups)

    def test_negated_capital_is_not_pass(self):
        self.assertEqual(self.verdict('TC-FA-01', 'Ottawa is not the capital of Canada; Toronto is.').status, 'FAIL')

    def test_wrong_capital_followed_by_correct_word_is_not_pass(self):
        self.assertNotEqual(self.verdict('TC-FA-01', 'Toronto is the capital of Canada, not Ottawa.').status, 'PASS')

    def test_quoted_capital_claim_needs_review(self):
        result = self.verdict('TC-FA-01', 'Someone said "Ottawa is the capital of Canada", but I disagree.')
        self.assertEqual(result.status, 'REVIEW')
        self.assertTrue(result.review_required)

    def test_negated_favorite_fails(self):
        self.assertEqual(self.verdict('TC-MEM-01', 'Your favorite animal is a dog, not a cat.').status, 'FAIL')

    def test_past_cat_current_dog_passes(self):
        self.assertEqual(self.verdict('AI-MEM-04', 'Your favorite used to be a cat; now it is a dog.').status, 'PASS')

    def test_ambiguous_favorite_needs_review(self):
        result = self.verdict('TC-MEM-01', 'Perhaps a cat, perhaps a dog; I cannot tell.')
        self.assertEqual(result.status, 'REVIEW')
        self.assertTrue(result.review_required)

    def test_self_contradictory_favorite_needs_review(self):
        self.assertEqual(self.verdict('TC-MEM-01', 'Your favorite animal is a cat, not a cat.').status, 'REVIEW')

    def test_flow_requires_real_hello_code(self):
        for code in ['I cannot provide Python code.', 'print("World")', 'print("Hello"', 'def hello():\n    pass']:
            with self.subTest(code=code):
                result = evaluate(self.cases['TC-FLOW-01'], [['OK', '12', code, 'Ottawa', 'cat']])
                self.assertEqual(result.status, 'FAIL')

    def test_fenced_hello_function_passes(self):
        code = 'Here is a function:\n```python\ndef hello():\n    print("Hello")\n```'
        self.assertEqual(evaluate(self.cases['TC-FLOW-01'], [['OK', '12', code, 'Ottawa', 'cat']]).status, 'PASS')

    def test_flow_reuses_capital_and_memory_checks(self):
        result = evaluate(self.cases['AI-FLOW-03'], [['OK', '12', 'OK', 'Ottawa is not the capital of Canada.', 'dog']])
        self.assertEqual(result.status, 'FAIL')

    def test_flow_cannot_pass_just_because_twelve_appears(self):
        result = evaluate(self.cases['TC-FLOW-01'], [['OK', '5 + 7 = 13, not 12.', 'print("Hello")', 'Ottawa', 'cat']])
        self.assertNotEqual(result.status, 'PASS')

    def test_contradictory_cpu_answer_is_not_pass(self):
        self.assertNotEqual(self.verdict('TC-FA-02', 'CPU does not mean Central Processing Unit.').status, 'PASS')

    def test_code_with_default_side_effect_is_reviewed_without_execution(self):
        with TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / 'must-not-exist'
            code = f'def hello(x=open({str(sentinel)!r}, "w")):\n    print("Hello")'
            result = evaluate(self.cases['TC-FLOW-01'], [['OK', '12', code, 'Ottawa', 'cat']])
            self.assertEqual(result.status, 'REVIEW')
            self.assertFalse(sentinel.exists())

    def test_code_shadowing_print_is_not_automatically_passed(self):
        code = 'def hello(print):\n    print("Hello")'
        self.assertEqual(evaluate(self.cases['TC-FLOW-01'], [['OK', '12', code, 'Ottawa', 'cat']]).status, 'REVIEW')

    def test_function_and_separate_usage_block_needs_review_not_failure(self):
        code = '```python\ndef hello():\n    print("Hello")\n```\nUsage:\n```python\nhello()\n```'
        self.assertEqual(evaluate(self.cases['TC-FLOW-01'], [['OK', '12', code, 'Ottawa', 'cat']]).status, 'REVIEW')


class TestCaptureRegressions(unittest.TestCase):
    def test_response_container_combines_all_text_parts(self):
        with TemporaryDirectory() as tmp:
            config = live_fakes.TestFakeAppiumAdapter()._config(tmp)
            data = json.loads(config.read_text())
            data['apps']['chatgpt']['selectors']['response_text_nodes'] = {'by': 'xpath', 'value': './/part'}
            config.write_text(json.dumps(data))
            driver = FakeMobileDriver()
            response = UIElement(driver, 'First paragraph')
            response.find_elements = lambda kind, value: [UIElement(driver, 'First paragraph'), UIElement(driver, 'Second paragraph')]
            driver.send_button.click = lambda: driver.responses.append(response)
            result = LiveAdapter(config, 'chatgpt', driver=driver).send('Question', 'TC-FA-01', 'turn1', Path(tmp) / 'shots')
            self.assertEqual(result, 'First paragraph\nSecond paragraph')

    def test_new_chat_opens_menu_before_clicking_new_chat(self):
        with TemporaryDirectory() as tmp:
            config = live_fakes.TestFakeAppiumAdapter()._config(tmp)
            data = json.loads(config.read_text())
            data['apps']['chatgpt']['selectors']['new_chat_menu_button'] = {'by': 'id', 'value': 'menu'}
            config.write_text(json.dumps(data))
            driver = FakeMobileDriver()
            actions = []
            menu = UIElement(driver)
            menu.click = lambda: actions.append('menu')
            driver.new_chat_button.click = lambda: actions.append('new')
            original = driver.find_elements
            driver.find_elements = lambda kind, value: [menu] if value == 'menu' else original(kind, value)
            LiveAdapter(config, 'chatgpt', driver=driver).new_chat()
            self.assertEqual(actions, ['menu', 'new'])

    def run_capture(self, folder, disappear=False):
        config = live_fakes.TestFakeAppiumAdapter()._config(folder)
        data = json.loads(config.read_text())
        data['apps']['chatgpt']['selectors']['response_finished_marker'] = {'by': 'id', 'value': 'finished'}
        config.write_text(json.dumps(data))
        driver = FakeMobileDriver()
        driver.send_button.click = lambda: driver.responses.append(UIElement(driver, 'Partial response'))
        original = driver.find_elements
        def find(kind, value):
            if value == 'finished':
                if disappear:
                    driver.responses = driver.responses[:1]
                else:
                    # Model a UI rerender replacing the element after the streaming pause.
                    driver.responses[-1] = UIElement(driver, 'Completed response: Ottawa.')
                return [UIElement(driver, 'Done')]
            return original(kind, value)
        driver.find_elements = find
        captured_at_screenshot = []
        def screenshot(path):
            captured_at_screenshot.append(driver.responses[-1].text)
            Path(path).write_bytes(b'FAKE_SCREENSHOT')
        driver.save_screenshot = screenshot
        adapter = LiveAdapter(config, 'chatgpt', driver=driver)
        result = adapter.send('Question', 'TC-FA-01', 'conversation1_turn1', Path(folder) / 'shots')
        return result, captured_at_screenshot

    def test_capture_rereads_replaced_bubble_after_completion(self):
        with TemporaryDirectory() as tmp:
            result, screenshots = self.run_capture(tmp)
            self.assertEqual(result, 'Completed response: Ottawa.')
            self.assertEqual(screenshots, [result])

    def test_missing_final_bubble_is_error_not_partial_capture(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(TimeoutError):
                self.run_capture(tmp, disappear=True)


class TestEvidenceRegressions(unittest.TestCase):
    def test_rerun_keeps_both_attempt_evidence_files(self):
        class EvidenceUI:
            fail = True
            def __init__(self, *args): pass
            def new_chat(self): pass
            def close(self): pass
            def send(self, prompt, case_id, turn, folder):
                if self.fail and turn.endswith('turn2'):
                    raise RuntimeError('simulated timeout')
                path = Path(folder) / f'chatgpt_{case_id}_{turn}.png'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('original' if self.fail else 'rerun')
                path.with_suffix('.xml').write_text('original XML' if self.fail else 'rerun XML')
                return 'OK' if turn.endswith('turn1') else 'cat'
        with TemporaryDirectory() as tmp:
            root = Path(tmp); config = root / 'config.json'; config.write_text('{}')
            out = root / 'run'
            run_live(config, 'chatgpt', 'TC-MEM-01', output=out, adapter_factory=EvidenceUI)
            original = next(out.rglob('*.png'))
            EvidenceUI.fail = False
            run_live(config, 'chatgpt', 'TC-MEM-01', output=out, resume=True, rerun_errors=True, adapter_factory=EvidenceUI)
            with (out / 'attempts.csv').open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([r['status'] for r in rows], ['ERROR', 'PASS'])
            self.assertNotEqual(rows[0]['evidence_directory'], rows[1]['evidence_directory'])
            self.assertEqual(original.read_text(), 'original')
            self.assertEqual(original.with_suffix('.xml').read_text(), 'original XML')
            for row in rows:
                self.assertIn(row['attempt_id'], row['evidence_directory'])


if __name__ == '__main__':
    unittest.main()
