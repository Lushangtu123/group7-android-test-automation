import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from console_core import validate_plan, safe_join, public_text, preview_allowed, RunManager, ReferenceStore

class PlanTests(unittest.TestCase):
 def test_quick_is_one_generated_case_two_apps_once(self):
  self.assertEqual(validate_plan({'profile':'quick'}),{'profile':'quick','app':'both','cases':['MB-GEN-009'],'repeats':1})
 def test_full_defaults_all_four_cases_twice(self):
  self.assertEqual(len(validate_plan({'profile':'full'})['cases']),4)
  self.assertEqual(validate_plan({'profile':'full'})['repeats'],2)
 def test_unknown_case_app_or_excessive_repeat_is_rejected(self):
  for data in [{'profile':'full','app':'shell'},{'profile':'full','cases':[';rm']},{'profile':'full','repeats':0},{'profile':'full','repeats':4},{'profile':'full','repeats':True},{'profile':'full','cases':[]}]:
   with self.assertRaises(ValueError):validate_plan(data)
 def test_quick_cannot_hide_arbitrary_case_selection(self):
  with self.assertRaises(ValueError):validate_plan({'profile':'quick','cases':['MB-GEN-013']})

class PrivacyTests(unittest.TestCase):
 def test_escape_paths_and_symlinks_rejected(self):
  with tempfile.TemporaryDirectory() as t,tempfile.TemporaryDirectory() as other:
   root=Path(t);(root/'escape').symlink_to(other,target_is_directory=True)
   for path in ['../../file','/etc/passwd','escape/file']:
    with self.assertRaises(ValueError):safe_join(root,path)
 def test_public_logs_redact_email_username_and_credentials(self):
  text=public_text('test@example.com /Users/someone/a {"access_token":"privatevalue"} Authorization: Bearer secrettoken0123456789')
  for value in ['test@example.com','/Users/someone','privatevalue','secrettoken0123456789']:self.assertNotIn(value,text)
 def test_preview_requires_verified_prompt_and_no_account_nodes(self):
  good='<hierarchy><node class="android.widget.EditText" text="Translate"/></hierarchy>'
  self.assertTrue(preview_allowed(good,['Translate']))
  self.assertFalse(preview_allowed(good,['Other']))
  self.assertFalse(preview_allowed(good.replace('</hierarchy>','<node text="account@example.com"/></hierarchy>'),['Translate']))
 def test_preview_does_not_allow_xml_external_entities(self):
  self.assertFalse(preview_allowed('<!DOCTYPE x><hierarchy/>',['x']))

class JobTests(unittest.TestCase):
 def manager(self,root):return RunManager(Path(root),launcher=lambda *a:None,preflight=lambda:{'ready':True})
 def test_single_active_job_and_restart_discovery(self):
  with tempfile.TemporaryDirectory() as t:
   m=self.manager(t);job=m.start({'profile':'quick'})
   with self.assertRaises(RuntimeError):m.start({'profile':'quick'})
   n=self.manager(t);self.assertEqual(n.jobs()[0]['id'],job['id']);self.assertEqual(n.jobs()[0]['state'],'INTERRUPTED')
 def test_unready_environment_creates_no_run(self):
  with tempfile.TemporaryDirectory() as t:
   m=RunManager(Path(t),preflight=lambda:{'ready':False,'checks':[]})
   with self.assertRaises(RuntimeError):m.start({'profile':'quick'})
   self.assertEqual(m.jobs(),[])
 def test_interrupted_job_does_not_invent_outcomes(self):
  with tempfile.TemporaryDirectory() as t:
   m=self.manager(t);job=m.start({'profile':'quick'});m.mark_ended(job['id'],interrupted=True)
   snapshot=m.snapshot(job['id']);self.assertEqual(snapshot['state'],'INTERRUPTED');self.assertEqual(snapshot['attempts'],[])
 def test_generation_keeps_immutable_independent_outputs(self):
  with tempfile.TemporaryDirectory() as t:
   m=self.manager(t);a=m.generate();b=m.generate()
   self.assertNotEqual(a['id'],b['id']);self.assertEqual(a['candidates'],16);self.assertEqual(a['executable'],4)
 def test_recorded_reference_stats_are_not_live(self):
  r=ReferenceStore();data=r.overview()
  self.assertEqual(data['formal']['counts'],{'PASS':37,'FAIL':0,'REVIEW':58,'ERROR':19})
  self.assertEqual(len(r.repeats()),114);self.assertEqual(len(r.reviews()),58)

class RestoredWorkerTests(unittest.TestCase):
 def test_restored_manager_finalizes_worker_that_ends_later(self):
  import os
  from console_core import atomic
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);m=RunManager(root,launcher=lambda *a:None,preflight=lambda:{'ready':True});job=m.start({'profile':'quick'});d=m.directory(job['id']);job['pid']=os.getpid();atomic(d/'job.json',job)
   restored=RunManager(root,launcher=lambda *a:None,preflight=lambda:{'ready':True})
   atomic(d/'summary.json',{'status_counts':{'PASS':2}});atomic(d/'execution_metadata.json',{'ended_utc':'2026-11-26T00:00:00+00:00','exit_code':0,'interrupted':False})
   self.assertEqual(restored.snapshot(job['id'])['state'],'COMPLETED')
 def test_clipboard_payload_is_not_exposed_in_public_logs(self):
  raw='[HTTP] --> POST /execute/sync {"script":"mobile: getClipboard"}\n{"value":"cHJpdmF0ZUBleGFtcGxlLmNvbQ=="}\n'
  self.assertNotIn('cHJpdmF0ZUBleGFtcGxlLmNvbQ==',public_text(raw))

class AccountLabelTests(unittest.TestCase):
 def test_private_display_name_is_not_served_as_ui_text(self):
  with patch('console_core.private_names',return_value=['Demo Person']):
   self.assertNotIn('Demo Person',public_text('Google Account: Demo Person; Keep all records'))
   self.assertIn('Keep all records',public_text('Keep all records'))
 def test_matching_prompt_does_not_make_an_account_avatar_safe(self):
  source='<hierarchy><node text="Translate"/><node content-desc="Google Account: Demo Person"/></hierarchy>'
  with patch('console_core.private_names',return_value=['Demo Person']):self.assertFalse(preview_allowed(source,['Translate']))

class ConsoleSnapshotTests(unittest.TestCase):
 def test_restart_after_completed_worker_uses_its_actual_summary(self):
  from console_core import atomic
  with tempfile.TemporaryDirectory() as t:
   m=RunManager(Path(t),launcher=lambda *a:None,preflight=lambda:{'ready':True});j=m.start({'profile':'quick'});d=m.directory(j['id']);atomic(d/'summary.json',{'status_counts':{'PASS':2}});atomic(d/'execution_metadata.json',{'ended_utc':'2026-11-26T00:00:00+00:00','exit_code':0,'interrupted':False})
   restored=RunManager(Path(t),launcher=lambda *a:None,preflight=lambda:{'ready':True});self.assertEqual(restored.snapshot(j['id'])['state'],'COMPLETED')
 def test_console_source_is_frozen_before_worker_launch(self):
  from console_core import ROOT
  import hashlib
  with tempfile.TemporaryDirectory() as t:
   observed=[]
   def launch(id,plan,directory):observed.append((directory/'console_snapshot/live_services.py').exists())
   m=RunManager(Path(t),launcher=launch,preflight=lambda:{'ready':True});job=m.start({'profile':'quick'});d=m.directory(job['id'])
   self.assertEqual(observed,[True]);manifest=json.loads((d/'console_source_sha256.json').read_text());self.assertEqual(manifest['live_services.py'],hashlib.sha256((ROOT/'live_services.py').read_bytes()).hexdigest())
