"""Group 7 test automation CLI. Offline replay must never be represented as real app test results."""
import argparse,csv,json,time,statistics
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from .catalog import ROOT,load_cases,discover
from .oracles import evaluate
from .augmentation import export_augmentations,export_generated_cases
from .fixture import seed_fixture
from .complexity import export as export_complexity

APPS=('chatgpt','gemini')

def _json(path,obj):
    path=Path(path);path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
def _csv(path,rows,cols=None):
    if not rows:return
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols or list(rows[0]),extrasaction='ignore');w.writeheader();w.writerows(rows)

def run(mode='replay',which='both',case_filter=None,output=None,config=None,inject_failure=False,repeats=1,resume=False,rerun_errors=False):
    if mode=='appium':
        if not config: raise ValueError('Appium mode requires --config with inspected selectors')
        from .live_runner import run_live
        return run_live(config,which,case_filter,repeats,output,resume,rerun_errors)
    cases=load_cases()
    if case_filter:
        targets=set(case_filter.split(','));cases=[c for c in cases if c.case_id in targets]
        if len(cases)!=len(targets):raise ValueError('One or more case IDs did not match catalog')
    selected=list(APPS) if which=='both' else [which]
    out=Path(output or (ROOT/'reports'/'local_replay'))
    out.mkdir(parents=True,exist_ok=True)
    if mode=='replay':
        path=ROOT/'fixtures'/'SYNTHETIC_replay_responses.json'
        if not path.exists():seed_fixture(path)
        fixture=json.loads(path.read_text(encoding='utf-8'))['apps']
    else:
        if not config:raise ValueError('Appium mode needs --config with real device selectors and capabilities')
        from .appium_adapter import LiveAdapter
    rows=[];details=[]
    for app in selected:
        adapter=None
        try:
            if mode=='appium':adapter=LiveAdapter(config,app)
            for case in cases:
                start=time.perf_counter()
                try:
                    if mode=='replay':
                        responses=json.loads(json.dumps(fixture[app][case.case_id]))
                        if inject_failure and app=='chatgpt' and case.case_id=='TC-FA-01':responses[-1][-1]='Montreal is the capital of Canada.'
                    else:
                        responses=[]
                        for conv_idx,group in enumerate(case.conversations):
                            adapter.new_chat() # separate session for each conversation group, including fairness pair
                            current=[]
                            for turn_idx,prompt in enumerate(group,1):
                                current.append(adapter.send(prompt,case.case_id,f'{conv_idx+1}_{turn_idx}',out/'screenshots'))
                            responses.append(current)
                    verdict=evaluate(case,responses)
                except Exception as exc:
                    verdict=None;responses=[];err=f'{type(exc).__name__}: {exc}'
                elapsed=time.perf_counter()-start
                row={'case_id':case.case_id,'application':app,'mode':'SYNTHETIC_REPLAY' if mode=='replay' else 'LIVE_APPIUM', 'status':verdict.status if verdict else 'ERROR','duration_seconds':round(elapsed,4), 'human_review_required':'YES' if (verdict and verdict.review_required) else 'NO','oracle':case.oracle,'note':verdict.note if verdict else err,'executed_at_utc':datetime.now(timezone.utc).isoformat()}
                rows.append(row)
                details.append({'case_id':case.case_id,'application':app,'mode':row['mode'],'prompts':case.conversations,'observed_responses':responses,'status':row['status'],'warning':'Synthetic educational fixture, not recorded AI application output' if mode=='replay' else 'Live automated UI capture; validate model/app versions and all qualitative oracles'})
        finally:
            if adapter:
                try:adapter.close()
                except Exception:pass
    _csv(out/'execution_results.csv',rows)
    summary={'run_mode':'SYNTHETIC_REPLAY_NOT_APPLICATION_TESTING' if mode=='replay' else 'LIVE_APPIUM_UI_AUTOMATION','timestamp_utc':datetime.now(timezone.utc).isoformat(),'planned_case_executions':len(rows),'counts':dict(Counter(x['status'] for x in rows)),'total_script_observed_seconds':round(sum(x['duration_seconds'] for x in rows),4),'mean_case_seconds':round(statistics.mean(x['duration_seconds'] for x in rows),5) if rows else 0,'automation_pass_rate_pct':round(100*sum(x['status']=='PASS' for x in rows)/len(rows),2) if rows else 0,'rate_scope':'Only synthetic replay fixture' if mode=='replay' else 'Automated check results for live app sessions; REVIEW requires human signoff', 'notes':['REVIEW cases are not counted as PASS.','A synthetic replay PASS only validates script/oracle plumbing.','The 38/38 historical Group 7 results are manual evidence from Deliverable #1/#2, not automation outcomes.']}
    _json(out/'summary.json',summary);_json(out/'response_details.json',details)
    return summary

def demo():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    d=discover(load_cases());_json(reports/'data_discovery.json',d)
    generated=export_generated_cases(reports/'generated_candidates.csv')
    aug=export_augmentations(reports/'augmented_variants.csv')
    scripts=export_complexity(reports/'script_complexity.csv')
    seed_fixture()
    summary=run()
    return {'discovered_cases':d['case_count'],'generated_candidates':len(generated),'augmentation_variants':len(aug),'analyzed_functions':len(scripts),'replay_counts':summary['counts']}

def cost_template():
    report_file=ROOT/'reports'/'local_replay'/'summary.json'
    replay_seconds=json.loads(report_file.read_text(encoding='utf-8'))['total_script_observed_seconds'] if report_file.exists() else None
    replay_minutes=f'{replay_seconds/60:.8f}' if replay_seconds is not None else ''
    rows=[
     {'activity':'Historical manual testing + screenshot recording (D#1)','minutes':'102','status':'PRIOR MANUAL REFERENCE (not normalized)','description':'Four testers; includes capture and manual work; not an automation run'},
     {'activity':'Local synthetic replay elapsed (D#3)','minutes':replay_minutes,'status':'MEASURED SYNTHETIC SCRIPT ONLY','description':'Synthetic script only, excludes app/model/network time'},
     {'activity':'Automation script development','minutes':'','status':'TEAM ENTRY REQUIRED','description':'Record individual effort from work logs'},
     {'activity':'Appium/device setup and configuration','minutes':'','status':'TEAM ENTRY REQUIRED','description':'Appium server / signing / locator inspection'},
     {'activity':'Live ChatGPT+Gemini automated execution','minutes':'','status':'LIVE EXECUTION REQUIRED','description':'Enter measured end-to-end app time'},
     {'activity':'Human review of qualitative outputs','minutes':'','status':'TEAM ENTRY REQUIRED','description':'NLU clarity and fairness comparison'},
     {'activity':'Debugging and maintenance','minutes':'','status':'TEAM ENTRY REQUIRED','description':'Locator/OS changes and flaky retries'},
    ];_csv(ROOT/'reports'/'automation_cost_worksheet.csv',rows);return rows

def historical():
    rows=[
      {'feature':'Factual/Domain','cases':5,'historical_app_results':10,'historical_pass':10},
      {'feature':'Memory','cases':5,'historical_app_results':10,'historical_pass':10},
      {'feature':'NLU','cases':6,'historical_app_results':12,'historical_pass':12},
      {'feature':'Fixed Flow','cases':3,'historical_app_results':6,'historical_pass':6},
    ];
    for r in rows:r['evidence_type']='PRIOR MANUAL REPORTS; NOT AUTOMATED';
    _csv(ROOT/'reports'/'historical_manual_results_REFERENCE.csv',rows)
    return rows

def make_template():
    rows=[{'case_id':c.case_id,'application':app,'execution_date':'','app_version':'','device_os':'','start_time':'','end_time':'','actual_response_file':'','status':'NOT_EXECUTED','reviewer':'','screenshot_file':''} for c in load_cases() for app in APPS]
    _csv(ROOT/'reports'/'live_execution_template.csv',rows)

def main(argv=None):
    parser=argparse.ArgumentParser(description='Group 7 Deliverable #3 reproducible automation toolkit')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('discover');sub.add_parser('generate');sub.add_parser('augment');sub.add_parser('complexity');sub.add_parser('demo')
    runp=sub.add_parser('run')
    runp.add_argument('--mode',choices=['replay','appium'],default='replay')
    runp.add_argument('--app',choices=['both','chatgpt','gemini'],default='both')
    runp.add_argument('--cases',default='',help='Comma-separated IDs; default all 19')
    runp.add_argument('--output',help='Directory for results')
    runp.add_argument('--config',help='Real Appium config JSON, needed only in appium mode')
    runp.add_argument('--inject-failure',action='store_true',help='Only for replay: intentionally corrupt one synthetic result')
    runp.add_argument('--repeats',type=int,default=1,help='Appium: repeat each case in fresh conversations')
    runp.add_argument('--resume',action='store_true',help='Appium: reuse checkpointed folder without duplicate records')
    runp.add_argument('--rerun-errors',action='store_true',help='Appium: rerun ERROR cases, keep previous attempts')
    args=parser.parse_args(argv)
    if args.command=='discover':result=discover(load_cases());_json(ROOT/'reports'/'data_discovery.json',result)
    elif args.command=='generate':result={'candidate_count':len(export_generated_cases(ROOT/'reports'/'generated_candidates.csv'))}
    elif args.command=='augment':result={'augmentation_count':len(export_augmentations(ROOT/'reports'/'augmented_variants.csv'))}
    elif args.command=='complexity':result={'function_count':len(export_complexity(ROOT/'reports'/'script_complexity.csv'))}
    elif args.command=='demo':result=demo();cost_template();historical();make_template()
    elif args.command=='run':result=run(args.mode,args.app,args.cases or None,args.output,args.config,args.inject_failure,args.repeats,args.resume,args.rerun_errors)
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
