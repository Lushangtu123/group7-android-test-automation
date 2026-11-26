import unittest
from group7_auto.catalog import Case
from group7_auto.model_based import concretize
from group7_auto.model_oracles import evaluate

class ModelGenerationTests(unittest.TestCase):
 def test_four_selected_coordinates_generate_distinct_executable_cases(self):
  rows=concretize()
  self.assertEqual({r['feature'] for r in rows},{'Factual/Domain','Memory','NLU','Fixed Flow'})
  self.assertEqual([r['generated_id'] for r in rows],['GEN-001','GEN-008','GEN-009','GEN-013'])
  self.assertEqual([sum(map(len,r['conversations'])) for r in rows],[1,3,1,5])
  self.assertTrue(all(r['human_approval']=='' for r in rows))
 def test_unreviewed_coordinate_cannot_silently_become_executable(self):
  with self.assertRaises(ValueError):concretize(selected_ids=['GEN-002'])

class ModelOracleTests(unittest.TestCase):
 def case(self,name,n):return Case('MB-X','Memory','','',name,[['prompt']*n],'',False,'Model extension')
 def test_memory_checks_interruption_and_recall(self):
  self.assertEqual(evaluate(self.case('opt_memory_dog14',3),[['Okay','14','dog']]).status,'PASS')
  self.assertEqual(evaluate(self.case('opt_memory_dog14',3),[['Okay','13','dog']]).status,'FAIL')
 def test_numeric_keyword_inside_explanation_is_not_pass(self):
  self.assertEqual(evaluate(self.case('opt_memory_dog14',3),[['Okay','14 is not the answer','dog']]).status,'REVIEW')
 def test_wrong_animal_is_not_pass(self):
  self.assertEqual(evaluate(self.case('opt_memory_dog14',3),[['Okay','14','cat']]).status,'FAIL')
 def test_incomplete_capture_is_error(self):
  self.assertEqual(evaluate(self.case('opt_memory_dog14',3),[['Okay','14']]).status,'ERROR')
 def test_flow_requires_all_independent_checkpoints(self):
  good=['Okay','14','def greet():\n    print("Hello")','Canberra','dog']
  self.assertEqual(evaluate(self.case('opt_flow_dog14_canberra',5),[good]).status,'PASS')
  wrong=good.copy();wrong[3]='Sydney'
  self.assertEqual(evaluate(self.case('opt_flow_dog14_canberra',5),[wrong]).status,'FAIL')
 def test_wrong_code_not_accepted_by_hello_word_mention(self):
  bad=['Okay','14','def greet():\n    print("not Hello")','Canberra','dog']
  self.assertEqual(evaluate(self.case('opt_flow_dog14_canberra',5),[bad]).status,'FAIL')
 def test_qualitative_nlu_stays_review(self):
  self.assertEqual(evaluate(self.case('manual_clarity',1),[['Plants use light.']]).status,'REVIEW')

class TranslationOracleTests(unittest.TestCase):
 def case(self):return Case('MB-TRANSLATE','NLU','','','opt_translate_fr_cat',[['Translate to French.']],'',False,'Model extension')
 def test_complete_french_translations_pass(self):
  for answer in ['Le chat dort.','Le chat est en train de dormir.']:
   self.assertEqual(evaluate(self.case(),[[answer]]).status,'PASS')
 def test_negated_or_wrong_animal_translation_fails(self):
  for answer in ['Le chat ne dort pas.','Le chien dort.']:
   self.assertEqual(evaluate(self.case(),[[answer]]).status,'FAIL')
 def test_quoted_mention_is_not_a_translation_pass(self):
  self.assertEqual(evaluate(self.case(),[['One could say Le chat dort, but I am not translating.']]).status,'REVIEW')

class CustomCatalogExecutionTests(unittest.TestCase):
 def test_every_extension_can_repeat_without_replacing_original_catalog(self):
  import csv,json
  from pathlib import Path
  from tempfile import TemporaryDirectory
  from group7_auto.model_based import export_executable
  from group7_auto.live_runner import run_live
  from group7_auto.catalog import load_cases
  answers={'MB-GEN-001':['Ottawa'],'MB-GEN-008':['Okay','14','dog'],'MB-GEN-009':['Le chat dort.'],'MB-GEN-013':['Okay','14','def greet():\n    print("Hello")','Canberra','dog']}
  class Fixture:
   def __init__(self,*a):pass
   def new_chat(self):self.index=0
   def send(self,prompt,case,*args):value=answers[case][self.index];self.index+=1;return value
   def close(self):pass
  with TemporaryDirectory() as t:
   root=Path(t);config=root/'config.json';config.write_text('{}');catalog=root/'extension.csv';export_executable(catalog)
   result=run_live(config,'both',repeats=2,output=root/'run',adapter_factory=Fixture,catalog_path=catalog)
   self.assertEqual(result['selected_records'],16);self.assertEqual(result['status_counts'],{'PASS':16})
   self.assertEqual(len(load_cases()),19)
