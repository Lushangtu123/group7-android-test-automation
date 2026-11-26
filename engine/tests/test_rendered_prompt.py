import unittest
import json
from tempfile import TemporaryDirectory
from group7_auto.android_snapshot import read_snapshot
from group7_auto.appium_adapter import LiveAdapter
import test_live_execution as fake

def source(text):
    return '<hierarchy><node resource-id="app:id/assistant_robin_user_message_text" text="'+text+'"/></hierarchy>'

class RenderedPromptTests(unittest.TestCase):
    def test_exact_prompt_remains_exact(self):
        state=read_snapshot(source('wat is the capitel of caneda?'),'gemini','wat is the capitel of caneda?')
        self.assertEqual(state['prompt_match'],'EXACT')

    def test_default_rejects_changed_capitalization(self):
        self.assertFalse(read_snapshot(source('Wat is the capitel of caneda?'),'gemini','wat is the capitel of caneda?')['prompt_present'])

    def test_explicit_policy_only_accepts_initial_uppercase_and_records_original_display(self):
        state=read_snapshot(source('Wat is the capitel of caneda?'),'gemini','wat is the capitel of caneda?',allow_initial_capitalization=True)
        self.assertTrue(state['prompt_present'])
        self.assertEqual(state['matched_prompt_text'],'Wat is the capitel of caneda?')
        self.assertEqual(state['prompt_match'],'INITIAL_ASCII_UPPERCASE_UI_VARIANT')

    def test_correction_or_full_casefold_is_rejected(self):
        for changed in ('What is the capital of Canada?','WAT IS THE CAPITEL OF CANEDA?','Wat is the capitel of Canada?'):
            self.assertFalse(read_snapshot(source(changed),'gemini','wat is the capitel of caneda?',allow_initial_capitalization=True)['prompt_present'])

    def test_uppercase_identifier_is_not_lowered(self):
        self.assertFalse(read_snapshot(source('cpu'),'gemini','CPU',allow_initial_capitalization=True)['prompt_present'])

    def test_initial_capitalization_policy_requires_verified_submission_and_atomic_capture(self):
        with TemporaryDirectory() as tmp:
            p=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(p.read_text());cfg['apps']['chatgpt']['allow_initial_capitalization']=True;p.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'capitalization'):
                LiveAdapter(p,'chatgpt',driver=fake.FakeMobileDriver())
