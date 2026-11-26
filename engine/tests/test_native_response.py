import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from group7_auto.appium_adapter import LiveAdapter
from html import escape
from group7_auto.native_response import gemini_native_view, prepend_overlapping

def xml(parts,prompt=True,footer=False,stop=False):
    user='<node resource-id="x:id/assistant_robin_user_message_text" text="Question" bounds="[200,326][1017,490]"/>' if prompt else ''
    body=''.join('<node class="android.widget.TextView" text="'+escape(t,quote=True)+'"/>' for t in parts)
    action='<node><node resource-id="x:id/assistant_robin_message_content_actions_options_button"/></node>' if footer else '<node/>'
    return '<hierarchy><node resource-id="x:id/assistant_robin_chat_history_list" bounds="[0,0][1080,2400]">'+user+'<node resource-id="x:id/assistant_robin_content_message_container" bounds="[63,528][1017,1849]">'+body+'</node>'+action+'</node>'+('<node content-desc="Stop generating response"/>' if stop else '')+'</hierarchy>'

class NativeResponseTests(unittest.TestCase):
    def test_generic_textviews_are_preserved_not_just_named_robin_text(self):
        result=gemini_native_view(xml(['First substantive paragraph.','Video pointer.'],footer=True),'Question',True)
        self.assertEqual(result['parts'],['First substantive paragraph.','Video pointer.'])
        self.assertTrue(result['start_prompt_confirmed']);self.assertTrue(result['footer_completed'])

    def test_native_code_language_label_is_not_merged_into_response_text(self):
        source=xml(['python'],footer=True).replace('<node class="android.widget.TextView" text="python"/>','<node class="android.widget.TextView" text="python" resource-id="x:id/assistant_robin_code_info"/><node class="android.widget.TextView" text="python" resource-id="x:id/assistant_robin_code_impl"/>')
        self.assertEqual(gemini_native_view(source,'Question',True)['parts'],['python'])

    def test_virtualized_prompt_requires_prior_current_turn_confirmation(self):
        with self.assertRaisesRegex(RuntimeError,'ownership'):
            gemini_native_view(xml(['Current body'],prompt=False),'Question',False)

    def test_ongoing_generation_is_never_a_complete_native_capture(self):
        with self.assertRaisesRegex(RuntimeError,'generating'):
            gemini_native_view(xml(['Still writing'],stop=True),'Question',True)

    def test_no_text_is_not_a_valid_answer(self):
        with self.assertRaisesRegex(RuntimeError,'text'):
            gemini_native_view(xml([]),'Question',True)

    def test_old_body_above_current_prompt_is_excluded(self):
        source=xml(['Current answer'],footer=True).replace('<node resource-id="x:id/assistant_robin_user_message_text"','<node resource-id="x:id/assistant_robin_content_message_container"><node class="android.widget.TextView" text="Old answer"/></node><node resource-id="x:id/assistant_robin_user_message_text"')
        self.assertEqual(gemini_native_view(source,'Question',True)['parts'],['Current answer'])

    def test_later_unexpected_prompt_rejects_old_answer_ownership(self):
        source=xml(['Current answer'],footer=True).replace('</hierarchy>','<node resource-id="x:id/assistant_robin_user_message_text" text="Other question"/></hierarchy>')
        with self.assertRaisesRegex(RuntimeError,'ownership'):
            gemini_native_view(source,'Question',True)

    def test_overlapping_viewports_preserve_all_ordered_paragraphs(self):
        a='First substantive paragraph with complete information.';b='Middle substantive paragraph with complete information.';c='Final substantive paragraph with complete information.'
        self.assertEqual(prepend_overlapping([a,b],[b,c]),([a,b,c],1))

    def test_gap_between_viewports_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError,'overlap'):
            prepend_overlapping(['Missing middle cannot be inferred.'],['Unrelated bottom must not be stitched.'])

    def test_ambiguous_short_repeated_item_is_not_an_overlap_proof(self):
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):
            prepend_overlapping(['Earlier paragraph','1.'],['1.','Later paragraph'])

    def test_repeated_paragraphs_are_not_globally_deduplicated(self):
        a='This is a sufficiently long repeated paragraph.'
        self.assertEqual(prepend_overlapping([a,a],[a,'Ending paragraph']),([a,a,'Ending paragraph'],1))

    def adapter(self,sources):
        class Driver:
            index=0
            @property
            def page_source(self):return sources[self.index]
            def save_screenshot(self,path):Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+str(self.index).encode())
            def execute_script(self,name,args):
                if args['startX']>=63:raise AssertionError('Gesture must begin in inspected non-text margin')
                self.index=min(self.index+1,len(sources)-1)
        a=LiveAdapter.__new__(LiveAdapter);a.driver=Driver();a.app='gemini';a.spec={};a.cfg={};a.stable=0;a.poll=0
        return a

    def test_adapter_saves_both_boundaries_and_exact_ordered_reconstruction(self):
        a='Beginning paragraph contains all required information.';b='Overlapping middle paragraph identifies this current answer.';c='Last paragraph.'
        adapter=self.adapter([xml([b,c],prompt=False,footer=True),xml([a,b],prompt=True)])
        with TemporaryDirectory() as tmp:
            prefix=Path(tmp)/'response';result=adapter._capture_complete_native_response('Question',prefix)
            self.assertEqual(result,'\n'.join([a,b,c]))
            proof=json.loads(Path(str(prefix)+'.native_proof.json').read_text())
            self.assertTrue(proof['complete_accessible_text_proven']);self.assertEqual(len(proof['views']),2)

    def test_adapter_preserves_partial_proof_and_rejects_a_viewport_gap(self):
        adapter=self.adapter([xml(['Bottom paragraph is not contiguous.'],prompt=False,footer=True),xml(['Start paragraph has a missing middle.'],prompt=True)])
        with TemporaryDirectory() as tmp:
            prefix=Path(tmp)/'response'
            with self.assertRaisesRegex(RuntimeError,'overlap'):
                adapter._capture_complete_native_response('Question',prefix)
            proof=json.loads(Path(str(prefix)+'.native_proof.json').read_text())
            self.assertFalse(proof['complete_accessible_text_proven']);self.assertEqual(len(proof['views']),2)

    def test_native_proof_requires_verified_atomic_gemini_configuration(self):
        import test_live_execution as fake
        with TemporaryDirectory() as tmp:
            config=fake.TestFakeAppiumAdapter()._config(tmp);cfg=json.loads(config.read_text())
            cfg['apps']['chatgpt']['native_full_response_capture']=True;config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'Native viewport proof'):
                LiveAdapter(config,'chatgpt',driver=fake.FakeMobileDriver())
