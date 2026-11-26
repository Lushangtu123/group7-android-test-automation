#!/usr/bin/env python3
"""Summarize actual attempts.csv, preserving FAIL, REVIEW and ERROR.

For any new live execution folder created by group7_auto.live_runner.
Never mixes historical manual or synthetic fixture results into live statistics.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def summarize(folder):
    folder=Path(folder)
    p=folder/'attempts.csv'
    meta=folder/'summary.json'
    if not meta.is_file():
        raise FileNotFoundError(f'No live-run summary.json in {folder}; refusing to label fixtures as live data')
    state=json.loads(meta.read_text(encoding='utf-8'))
    if state.get('run_type') != 'LIVE_APPIUM_UI' or state.get('evidence_source') != 'THIS_RUN_ONLY':
        raise ValueError('This folder is not recorded as a genuine Appium UI run')
    if not p.is_file(): raise FileNotFoundError(f'No live attempts.csv in {folder}')
    with p.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    if not rows: raise ValueError('No attempts found')
    latest={}
    for row in rows:
        key=(row['application'],row['case_id'],row['repeat'])
        latest[key]=row
    selected=list(latest.values())
    counts=Counter(row['status'] for row in selected)
    apps={}
    for app in sorted({r['application'] for r in selected}):
        ar=[r for r in selected if r['application']==app]
        ac=Counter(r['status'] for r in ar)
        apps[app]={'records':len(ar), **{status:ac.get(status,0) for status in ('PASS','FAIL','REVIEW','ERROR')}}
    total=len(selected)
    result={
        'source':'LIVE_ATTEMPTS_CSV_FROM_THIS_DIRECTORY_ONLY',
        'all_checkpointed_attempts':len(rows), 'selected_latest_app_case_repeat_records':total,
        'counts':{status:counts.get(status,0) for status in ('PASS','FAIL','REVIEW','ERROR')},
        'automatic_pass_rate_pct':round(counts['PASS']*100/total,2) if total else None,
        'completed_non_error_rate_pct':round((total-counts['ERROR'])*100/total,2) if total else None,
        'selected_case_minutes':round(sum(float(r['duration_seconds']) for r in selected)/60,4),
        'all_checkpointed_case_minutes':round(sum(float(r['duration_seconds']) for r in rows)/60,4),
        'by_application':apps,
        'limitations':['REVIEW is not PASS.','ERROR may indicate UI capture problems.','Case durations omit setup/human work.']
    }
    out=folder/'live_statistics_for_report.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('live_folder',help='e.g. reports/pilot_chatgpt_YYYYMMDD_HHMMSS')
    args=p.parse_args()
    s=summarize(args.live_folder)
    print(json.dumps(s,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
