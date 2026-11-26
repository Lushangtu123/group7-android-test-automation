import unittest
import xml.etree.ElementTree as ET
from group7_auto.android_snapshot import is_reply_control_label

class ReplyControlLabelTests(unittest.TestCase):
    def test_inspected_wrapped_button_label_is_ui_metadata(self):
        root=ET.fromstring('<node clickable="true"><node class="android.widget.TextView" text="Learn more"/><node class="android.widget.Button"/></node>')
        self.assertTrue(is_reply_control_label(root[0],{c:n for n in root.iter() for c in n}))

    def test_identical_prose_is_not_removed_by_its_words(self):
        root=ET.fromstring('<node><node class="android.widget.TextView" text="Learn more"/></node>')
        self.assertFalse(is_reply_control_label(root[0],{root[0]:root}))

    def test_accessible_body_or_link_text_is_not_a_button_label(self):
        root=ET.fromstring('<node clickable="true"><node class="android.widget.TextView" text="Substantive response" content-desc="Substantive response"/><node class="android.widget.Button"/></node>')
        self.assertFalse(is_reply_control_label(root[0],{c:n for n in root.iter() for c in n}))
