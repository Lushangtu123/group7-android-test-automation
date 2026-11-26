import unittest
from group7_auto.response_agreement import agrees_with_visible_text

class ResponseAgreementTests(unittest.TestCase):
    def test_virtualized_numbered_native_list_matches_full_markdown_copy(self):
        visible = '2.\nA compromise was reached in 1901.\n3.\nCanberra was selected in 1908.\nSources'
        copied = 'Actually, Canberra is the capital.\n\n* A compromise was reached in 1901.\n\n* Canberra was selected in 1908.'
        self.assertTrue(agrees_with_visible_text(visible, copied))

    def test_common_opening_does_not_hide_different_following_content(self):
        self.assertFalse(agrees_with_visible_text('Here is the answer.\nThe result is 30.', 'Here is the answer.\nThe result is 31.'))

    def test_formatting_only_text_cannot_verify_a_copy(self):
        self.assertFalse(agrees_with_visible_text('2.\nSources', 'Something from 1927.'))

    def test_short_answer_has_token_boundaries(self):
        self.assertTrue(agrees_with_visible_text('30', '**30**'))
        self.assertFalse(agrees_with_visible_text('30', '130'))

    def test_code_identifier_difference_is_preserved(self):
        self.assertFalse(agrees_with_visible_text('return first_value + second_value', 'return firstvalue + secondvalue'))

    def test_native_text_is_not_replaced_by_its_normalized_version(self):
        visible = 'The capital is Ottawa.\nIt is in Ontario.'
        self.assertTrue(agrees_with_visible_text(visible, '**The capital is Ottawa.**\nIt is in Ontario.'))

    def test_unrelated_old_response_is_rejected(self):
        self.assertFalse(agrees_with_visible_text('The capital is Canberra.', 'The capital is Ottawa.'))

    def test_accessible_inline_link_label_matches_markdown_label(self):
        native = 'You can follow announcements on the official Nobel Prize website\u2060\ufffc.'
        copied = 'You can follow announcements on the [official Nobel Prize website](https://www.nobelprize.org/).'
        self.assertTrue(agrees_with_visible_text(native, copied))

    def test_inline_link_label_must_match(self):
        self.assertFalse(agrees_with_visible_text('Visit the official Nobel site\u2060\ufffc.',
                         'Visit the [unofficial Nobel site](https://example.org/).'))

    def test_visible_url_is_checked_instead_of_discarded(self):
        self.assertFalse(agrees_with_visible_text('Visit https://nobelprize.org/\u2060\ufffc.',
                         'Visit [the official site](https://example.org/).'))
