import unittest
from group7_auto.android_snapshot import read_snapshot

class AtomicSnapshotTests(unittest.TestCase):
 def test_same_snapshot_cannot_complete_while_current_generation_visible(self):
  xml='<hierarchy><node class="android.widget.TextView" text="Question"/><node class="android.view.View" content-desc="Copy"/><node content-desc="Stop"/></hierarchy>'
  self.assertTrue(read_snapshot(xml,'chatgpt','Question')['generating'])
 def test_system_clipboard_overlay_is_reported_separately(self):
  xml='<hierarchy><node package="com.openai.chatgpt" text="Reply"/><node package="com.android.systemui" resource-id="com.android.systemui:id/clipboard_overlay"/><node package="com.android.systemui" resource-id="com.android.systemui:id/dismiss_button" content-desc="Dismiss"/></hierarchy>'
  state=read_snapshot(xml,'chatgpt','Question')
  self.assertTrue(state['clipboard_overlay'])
  self.assertFalse(state['reply_completed'])
 def test_previous_reply_above_current_prompt_is_not_current(self):
  xml='<hierarchy><node class="android.widget.TextView" text="old" content-desc="old"/><node content-desc="Copy"/><node class="android.widget.TextView" text="Question"/></hierarchy>'
  self.assertFalse(read_snapshot(xml,'chatgpt','Question')['reply_completed'])

 def test_atomic_current_answer_and_done_footer_are_from_same_tree(self):
  body='<node class="android.view.View"><node class="android.widget.TextView" text="Your favorite animal is a cat." content-desc="Your favorite animal is a cat."/>{}</node>'
  copy='<node content-desc="Copy"/>'
  for _ in range(5):copy='<node class="android.view.View">'+copy+'</node>'
  xml='<hierarchy><node class="android.widget.TextView" text="Question"/>'+body.format(copy)+'</hierarchy>'
  state=read_snapshot(xml,'chatgpt','Question')
  self.assertTrue(state['reply_completed'])
  self.assertEqual(state['reply']['text'],'Your favorite animal is a cat.')
 def test_copy_above_prompt_does_not_signal_completion(self):
  copy='<node content-desc="Copy"/>'
  for _ in range(5):copy='<node>'+copy+'</node>'
  xml='<hierarchy><node><node class="android.widget.TextView" text="Prior answer"/>'+copy+'</node><node class="android.widget.TextView" text="Question"/></hierarchy>'
  self.assertFalse(read_snapshot(xml,'chatgpt','Question')['reply_completed'])

 def test_long_reply_body_is_observed_before_footer_enters_viewport(self):
  xml='<hierarchy><node class="android.widget.TextView" text="Question"/><node class="android.widget.TextView" text="Long current answer" content-desc="Long current answer" bounds="[42,600][1037,2400]"/></hierarchy>'
  state=read_snapshot(xml,'chatgpt','Question')
  self.assertIsNotNone(state['reply'])
  self.assertEqual(state['reply']['text'],'Long current answer')
  self.assertFalse(state['reply_completed'])

 def test_visible_current_body_can_be_observed_after_confirmed_prompt_is_virtualized(self):
  xml='<hierarchy><node class="android.widget.TextView" text="Continued answer" content-desc="Continued answer" bounds="[42,500][1037,2400]"/></hierarchy>'
  state=read_snapshot(xml,'chatgpt','Question',prompt_seen=True)
  self.assertEqual(state['reply']['text'],'Continued answer')
  self.assertFalse(state['reply_completed'])
