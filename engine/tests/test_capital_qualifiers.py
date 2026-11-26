import unittest
from group7_auto.catalog import load_cases
from group7_auto.oracles import evaluate


class TestCapitalQualifiers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = next(c for c in load_cases() if c.case_id == 'TC-FA-01')

    def status(self, text):
        return evaluate(self.case, [[text]]).status

    def test_original_chatgpt_answer_is_supported(self):
        self.assertEqual(self.status('The capital of Canada is Ottawa, in the province of Ontario. 🇨🇦'), 'PASS')

    def test_original_gemini_answer_is_supported(self):
        self.assertEqual(self.status('The capital of Canada is Ottawa, located in the province of Ontario.'), 'PASS')

    def test_negation_with_correct_geography_does_not_pass(self):
        self.assertEqual(self.status('Ottawa is not the capital of Canada, located in the province of Ontario.'), 'FAIL')

    def test_wrong_capital_in_ontario_does_not_pass(self):
        self.assertEqual(self.status('The capital of Canada is Toronto, located in the province of Ontario.'), 'FAIL')

    def test_wrong_province_requires_review(self):
        self.assertEqual(self.status('The capital of Canada is Ottawa, located in the province of Quebec.'), 'REVIEW')

    def test_extra_contradiction_requires_review(self):
        self.assertNotEqual(self.status('The capital of Canada is Ottawa, located in the province of Ontario, but Toronto is the real capital.'), 'PASS')

    def test_quoted_answer_requires_review(self):
        self.assertEqual(self.status('Someone claimed "The capital of Canada is Ottawa, located in the province of Ontario", but that is false.'), 'REVIEW')

    def test_unchecked_geography_is_not_accepted(self):
        self.assertEqual(self.status('The capital of Canada is Ottawa, located in France.'), 'REVIEW')


if __name__ == '__main__':
    unittest.main()
