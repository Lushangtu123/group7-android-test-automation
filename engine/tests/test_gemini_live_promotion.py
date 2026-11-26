import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from group7_auto.native_response import gemini_native_view
PROMPT='Translate this sentence into French: The cat is sleeping. Reply with only the French sentence.'
SOURCE=(Path(__file__).parent/'fixtures/gemini_live_promo.xml').read_text()
class GeminiLivePromotionTests(unittest.TestCase):
 def test_actual_actionable_promotion_is_excluded_and_audited(self):
  v=gemini_native_view(SOURCE,PROMPT,True)
  self.assertEqual(v['parts'],['Le chat dort.\n'])
  self.assertEqual(v['excluded_ui_metadata'][0]['kind'],'INSPECTED_GEMINI_LIVE_PROMOTION')
 def test_same_words_in_real_response_are_retained(self):
  root=ET.fromstring(SOURCE);parents={c:n for n in root.iter() for c in n}
  for n in list(root.iter()):
   if n.get('class')=='android.widget.FrameLayout' and n.get('is-collection-item')=='true':
    if any(x.get('class')=='androidx.compose.ui.platform.ComposeView' for x in n):parents[n].remove(n)
   if n.get('resource-id','').endswith('assistant_robin_text'):n.set('text','Talk about this with Gemini Live. Try a real-time voice conversation.')
  self.assertEqual(gemini_native_view(ET.tostring(root,encoding='unicode'),PROMPT,True)['parts'],['Talk about this with Gemini Live. Try a real-time voice conversation.'])
 def test_unknown_title_is_not_filtered(self):
  changed=SOURCE.replace('Talk about this with Gemini Live','Unrecognized callout')
  self.assertIn('Unrecognized callout',gemini_native_view(changed,PROMPT,True)['parts'])
 def test_missing_button_role_prevents_filtering(self):
  changed=SOURCE.replace('class="android.widget.Button"','class="android.view.View"')
  self.assertIn('Talk about this with Gemini Live',gemini_native_view(changed,PROMPT,True)['parts'])
 def test_other_window_control_cannot_authorize_exclusion(self):
  root=ET.fromstring(SOURCE)
  for n in root.iter():
   if n.get('text')=='Try a real-time voice conversation':n.set('window-id','different')
  self.assertIn('Talk about this with Gemini Live',gemini_native_view(ET.tostring(root,encoding='unicode'),PROMPT,True)['parts'])
