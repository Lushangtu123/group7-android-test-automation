import unittest
import xml.etree.ElementTree as ET
from group7_auto.android_snapshot import is_code_language_badge

class CodeLanguageBadgeTests(unittest.TestCase):
    def test_inspected_code_header_label_is_metadata(self):
        root=ET.fromstring('<node><node content-desc="Code block"/><node class="android.widget.TextView" text="Python"/></node>')
        parents={c:n for n in root.iter() for c in n}
        self.assertTrue(is_code_language_badge(root[1],parents))

    def test_prose_word_python_is_not_removed(self):
        root=ET.fromstring('<node><node class="android.widget.TextView" text="Python"/></node>')
        self.assertFalse(is_code_language_badge(root[0],{root[0]:root}))

    def test_code_body_containing_python_is_not_removed(self):
        root=ET.fromstring('<node><node content-desc="Code block"/><node class="android.widget.TextView" text="Python" content-desc="Python"/></node>')
        self.assertFalse(is_code_language_badge(root[1],{c:n for n in root.iter() for c in n}))

    def test_gemini_inspected_code_info_resource_is_language_metadata(self):
        node=ET.fromstring('<node class="android.widget.TextView" text="python" resource-id="com.google.android.googlequicksearchbox:id/assistant_robin_code_info"/>')
        self.assertTrue(is_code_language_badge(node,{}))

    def test_gemini_code_implementation_with_same_word_is_not_metadata(self):
        node=ET.fromstring('<node class="android.widget.TextView" text="python" resource-id="com.google.android.googlequicksearchbox:id/assistant_robin_code_impl"/>')
        self.assertFalse(is_code_language_badge(node,{}))
