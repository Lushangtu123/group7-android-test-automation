import unittest
from group7_auto.catalog import load_cases, discover
from group7_auto.oracles import evaluate
from group7_auto.fixture import T
from group7_auto.augmentation import export_augmentations, export_generated_cases
from tempfile import TemporaryDirectory
from pathlib import Path

class TestGroup7Automation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases={c.case_id:c for c in load_cases()}
    def check(self,k,responses,expected):
        c=self.cases[k];return self.assertEqual(evaluate(c,responses).status,expected)
    def test_catalog_19(self):self.assertEqual(len(self.cases),19)
    def test_catalog_features(self):self.assertEqual(discover(list(self.cases.values()))['feature_counts'],{'Factual/Domain':5,'Fixed Flow':3,'Memory':5,'NLU':6})
    def test_requirements_covered(self):self.assertFalse(discover(list(self.cases.values()))['missing_requirements'])
    def test_ottawa_success(self):self.check('TC-FA-01',[['Ottawa.']],'PASS')
    def test_ottawa_failure(self):self.check('TC-FA-01',[['Montreal.']],'FAIL')
    def test_cpu(self):self.check('TC-FA-02',[['CPU is Central Processing Unit.']],'PASS')
    def test_sydney(self):self.check('TC-FA-03',[['Sydney is incorrect; Canberra is the capital.']],'PASS')
    def test_dog(self):self.check('AI-MEM-04',[['ok','updated','Dog is the current favorite.']],'PASS')
    def test_wrong_dog(self):self.check('AI-MEM-04',[['ok','updated','Your favorite animal is cat.']],'FAIL')
    def test_future_unknown(self):self.check('AI-FA-05',[['The winner of the 2030 Nobel Prize has not yet been announced.']],'PASS')
    def test_unfounded_future_winner(self):self.check('AI-FA-05',[['The 2030 Nobel Prize was awarded to Alice Smith.']],'FAIL')
    def test_ambiguous(self):self.check('AI-NLU-05',[['Which country do you mean?']],'PASS')
    def test_pair_requires_review(self):self.check('AI-NLU-06',[[T['AI-NLU-06'][0][0]],[T['AI-NLU-06'][1][0]]],'REVIEW')
    def test_clarity_requires_review(self):self.check('TC-NLU-04',[T['TC-NLU-04']],'REVIEW')
    def test_flow_correct(self):self.check('TC-FLOW-01',[T['TC-FLOW-01']],'PASS')
    def test_flow_wrong(self):
        responses=list(T['TC-FLOW-01']);responses[1]='5 + 7 = 13'
        self.check('TC-FLOW-01',[responses],'FAIL')
    def test_augmentation_count(self):
        with TemporaryDirectory() as t:self.assertEqual(len(export_augmentations(Path(t)/'a.csv')),8)
    def test_generated_count(self):
        with TemporaryDirectory() as t:self.assertEqual(len(export_generated_cases(Path(t)/'g.csv')),16)

if __name__=='__main__':unittest.main()
