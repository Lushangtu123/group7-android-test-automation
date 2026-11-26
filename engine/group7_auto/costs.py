"""Auditable duration/cost worksheet with NO invented labor or financial charges."""
import argparse
import csv
import json
from pathlib import Path
from .catalog import ROOT

# Provenance: user-provided FINAL_REPORT.md, not independently auditable raw CSV.
TEAM_REPORTED_ATTEMPTS = 74
TEAM_REPORTED_ATTEMPT_SECONDS = 2066.4029
TEAM_REPORTED_SELECTED = 38
TEAM_REPORTED_SELECTED_SECONDS = 1415.3414
TEAM_PRIOR_MANUAL_PERSON_MIN = 102
PERSONNEL = ['Yinqi Chen','Greg Lu','Jonas Quiballo','Nolan Antonio']
LABOR_CATEGORIES = ['script_development','environment_setup','debugging_maintenance','human_qualitative_review']


def make_worklog(path):
    path=Path(path)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['tester','activity','actual_person_minutes','evidence_note'])
        w.writeheader()
        for name in PERSONNEL:
            for activity in LABOR_CATEGORIES:
                w.writerow({'tester':name,'activity':activity,'actual_person_minutes':'',
                            'evidence_note':'[DATA REQUIRED] actual time log or recollection; do not guess'})
    return path


def evaluate_worklog(path):
    with Path(path).open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    entered=[]
    for row in rows:
        raw=row.get('actual_person_minutes','').strip()
        if not raw: continue
        value=float(raw)
        if value<0: raise ValueError('Actual person minutes cannot be negative')
        entered.append((row['activity'],value))
    complete=bool(rows) and len(entered)==len(rows)
    return {
        'entries_filled':len(entered), 'entries_total':len(rows),
        'person_minutes_total_if_complete':round(sum(v for k,v in entered),4) if complete else None,
        'partial_minutes_recorded_NOT_TOTAL':round(sum(v for k,v in entered),4),
        'completion':'COMPLETE' if complete else 'DATA REQUIRED',
    }


def reported_costs(worklog_path=None, case_csv=None):
    # These are actual prior-reported execution DURATIONS, not dollars or person-time.
    data={
      'provenance':'FINAL_REPORT.md supplied by team; raw 74-attempt audit CSV not available in current material',
      'checkpointed_attempt_count':TEAM_REPORTED_ATTEMPTS,
      'checkpointed_duration_s':TEAM_REPORTED_ATTEMPT_SECONDS,
      'checkpointed_duration_min':round(TEAM_REPORTED_ATTEMPT_SECONDS/60,4),
      'selected_case_count':TEAM_REPORTED_SELECTED,
      'selected_case_duration_s':TEAM_REPORTED_SELECTED_SECONDS,
      'selected_case_duration_min':round(TEAM_REPORTED_SELECTED_SECONDS/60,4),
      'superseded_checkpointed_duration_s':round(TEAM_REPORTED_ATTEMPT_SECONDS-TEAM_REPORTED_SELECTED_SECONDS,4),
      'superseded_checkpointed_duration_min':round((TEAM_REPORTED_ATTEMPT_SECONDS-TEAM_REPORTED_SELECTED_SECONDS)/60,4),
      'prior_manual_reference_person_min':TEAM_PRIOR_MANUAL_PERSON_MIN,
      'matched_manual_comparison':'NOT MEASURED - previous 102 person-min includes different work and team tasks',
      'financial_automation_cost':'NOT MEASURED',
      'automation_development_labor':'DATA REQUIRED',
      'no_savings_estimate_without_matched_measurement':True,
    }
    if case_csv:
        with Path(case_csv).open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
        if not rows:raise ValueError('No case rows')
        durations=[float(r['duration_seconds']) for r in rows]
        if any(d<0 for d in durations):raise ValueError('Negative duration')
        data['new_run_attempts']=len(rows)
        data['new_run_checkpointed_duration_s']=round(sum(durations),4)
        data['new_run_source']=str(case_csv)
        data['new_run_note']='Independent NEW local execution log; do not add to reported historical totals without reconciliation'
    if worklog_path:
        data['labor_entries']=evaluate_worklog(worklog_path)
    return data


def main(argv=None):
    ap=argparse.ArgumentParser(description='Generate transparent automation cost statement')
    ap.add_argument('--worklog',default=str(ROOT/'reports'/'team_labor_times_template.csv'))
    ap.add_argument('--live-results',help='Optional NEW run attempts.csv')
    ap.add_argument('--output',default=str(ROOT/'reports'/'automation_cost_summary.json'))
    args=ap.parse_args(argv)
    make_worklog(args.worklog)
    summary=reported_costs(args.worklog,args.live_results)
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
