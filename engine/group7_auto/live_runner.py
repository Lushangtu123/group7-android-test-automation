"""Checkpointed, repeatable Android Appium executor for the 19 Group 7 cases.

This is reconstructed code: independently testable, but must be configured and
validated on the team's Android device before any claim of live execution.
"""
import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .catalog import ROOT, load_cases
from .model_oracles import evaluate

APPS = ('chatgpt', 'gemini')
FIELDS = ('attempt_id','case_id','feature','application','repeat','status','oracle',
          'duration_seconds','started_utc','ended_utc','completed_turns',
          'planned_turns','human_review_required','note','evidence_directory')


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def save_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def save_csv_atomic(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.tmp')
    with tmp.open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def append_jsonl(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=False)+'\n')
        fh.flush()


def run_live(config, which='both', case_ids=None, repeats=1, output=None,
             resume=False, rerun_errors=False, adapter_factory=None, catalog_path=None):
    if repeats < 1:
        raise ValueError('--repeats must be at least 1')
    cases = load_cases(catalog_path)
    if case_ids:
        ids = [s.strip() for s in case_ids.split(',') if s.strip()]
        wanted = set(ids)
        cases = [c for c in cases if c.case_id in wanted]
        if len(cases) != len(wanted):
            raise ValueError('Unknown case ID in --cases')
    apps = APPS if which == 'both' else (which,)
    if any(app not in APPS for app in apps):
        raise ValueError('Unknown application')
    if not Path(config).is_file():
        raise FileNotFoundError(f'No verified Appium config: {config}')
    out = Path(output) if output else (ROOT/'reports'/f'live_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{uuid4().hex[:6]}')
    result_path = out/'attempts.csv'
    if result_path.exists() and not resume:
        raise FileExistsError(f'Output already contains attempts; use --resume or choose another output: {out}')
    old = []
    if result_path.exists():
        with result_path.open(encoding='utf-8', newline='') as fh:
            old = list(csv.DictReader(fh))
    plan = {(app,c.case_id,r) for app in apps for c in cases for r in range(1,repeats+1)}
    completed = set()
    for r in old:
        if (r['application'],r['case_id'],int(r['repeat'])) in plan:
            if r['status'] != 'ERROR' or not rerun_errors:
                completed.add((r['application'],r['case_id'],int(r['repeat'])))
    if adapter_factory is None:
        from .appium_adapter import LiveAdapter
        adapter_factory = LiveAdapter
    out.mkdir(parents=True, exist_ok=True)
    rows = list(old)
    for app in apps:
        tasks = [(c,rep) for rep in range(1,repeats+1) for c in cases
                 if (app,c.case_id,rep) not in completed]
        if not tasks:
            continue
        adapter = None
        startup_error = None
        try:
            adapter = adapter_factory(config,app)
        except Exception as exc:
            startup_error = f'{type(exc).__name__}: {exc}'
        try:
            for case, rep in tasks:
                attempt_id = uuid4().hex[:12]
                start_clock = time.perf_counter()
                start = utc_now()
                evidence_dir = out/'screenshots'/app/case.case_id/f'repeat_{rep}'/attempt_id
                planned_turns = sum(map(len,case.conversations))
                captured = []
                captured_turn_count = 0
                note = ''
                status = 'ERROR'
                review_required = 'NO'
                if startup_error:
                    note = 'SESSION_START_ERROR: '+startup_error
                else:
                    try:
                        for conv_num, group in enumerate(case.conversations,1):
                            # Each independent paired prompt gets its own new chat.
                            prepare = getattr(adapter, 'prepare_conversation', None)
                            if callable(prepare):
                                prepare(evidence_dir, conv_num)
                            adapter.new_chat()
                            current=[]
                            captured.append(current)
                            for turn_num,prompt in enumerate(group,1):
                                answer = adapter.send(prompt, case.case_id,
                                    f'conversation{conv_num}_turn{turn_num}', evidence_dir)
                                current.append(answer)
                                captured_turn_count += 1
                                append_jsonl(out/'turn_checkpoints.jsonl',{
                                    'attempt_id':attempt_id,'application':app,'case_id':case.case_id,
                                    'repeat':rep,'conversation':conv_num,'turn':turn_num,
                                    'prompt':prompt,'response':answer,'captured_at_utc':utc_now(),
                                    'capture_type':'LIVE_APPIUM_UI_TEXT'
                                })
                        verdict = evaluate(case,captured)
                        status = verdict.status
                        note = verdict.note
                        review_required = 'YES' if verdict.review_required else 'NO'
                    except Exception as exc:
                        status='ERROR'
                        note=f'{type(exc).__name__}: {exc}'
                        capture_error = getattr(adapter, 'capture_error', None)
                        if callable(capture_error):
                            try:
                                capture_error(evidence_dir)
                            except Exception as evidence_exc:
                                append_jsonl(out/'session_errors.jsonl', {
                                    'application':app, 'attempt_id':attempt_id,
                                    'event':'ERROR_EVIDENCE_CAPTURE_FAILED',
                                    'message':str(evidence_exc), 'timestamp_utc':utc_now()})
                duration=round(time.perf_counter()-start_clock,4)
                record={
                    'attempt_id':attempt_id,'case_id':case.case_id,'feature':case.feature,
                    'application':app,'repeat':rep,'status':status,'oracle':case.oracle,
                    'duration_seconds':duration,'started_utc':start,'ended_utc':utc_now(),
                    'completed_turns':captured_turn_count, 'planned_turns':planned_turns,
                    'human_review_required':review_required,'note':note,
                    'evidence_directory':str(evidence_dir.relative_to(out)),
                }
                # Preserve failed attempt records instead of editing them into PASS.
                rows.append(record)
                save_csv_atomic(result_path,rows)
                append_jsonl(out/'response_details.jsonl',{
                    **record, 'input_groups':case.conversations,
                    'captured_response_groups':captured,
                    'warning':'A recorded live UI capture is not a semantic truth guarantee'
                })
        finally:
            if adapter is not None:
                try:
                    adapter.close()
                except Exception as exc:
                    append_jsonl(out/'session_errors.jsonl',{
                        'application':app,'event':'SESSION_CLOSE_ERROR',
                        'message':str(exc),'timestamp_utc':utc_now()})
    relevant=[r for r in rows if (r['application'],r['case_id'],int(r['repeat'])) in plan]
    latest={}
    for row in relevant:
        latest[(row['application'],row['case_id'],int(row['repeat']))]=row
    final=list(latest.values())
    counts=Counter(r['status'] for r in final)
    summary={
        'run_type':'LIVE_APPIUM_UI', 'evidence_source':'THIS_RUN_ONLY',
        'config_path':str(config), 'output_dir':str(out),
        'planned_app_case_repetitions':len(plan), 'selected_records':len(final),
        'all_checkpointed_attempts':len(relevant), 'status_counts':dict(counts),
        'automatic_pass_rate_pct':round(100*counts.get('PASS',0)/len(final),2) if final else None,
        'completion_rate_pct':round(100*(len(final)-counts.get('ERROR',0))/len(plan),2) if plan else None,
        'selected_recorded_case_seconds':round(sum(float(r['duration_seconds']) for r in final),4),
        'checkpointed_attempt_seconds':round(sum(float(r['duration_seconds']) for r in relevant),4),
        'notes':['Captured live UI output must be checked on the actual device.',
                 'REVIEW is not PASS; requires a separate human judgment.',
                 'ERROR denotes capture/infrastructure failure, not necessarily model failure.',
                 'Recorded duration does not include uncheckpointed setup or human effort.',
                 'These outputs do not authenticate earlier team reports.'],
        'timestamp_utc':utc_now(),
    }
    save_json_atomic(out/'summary.json',summary)
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description='Group 7 checkpointed Android Appium runner')
    ap.add_argument('--config',required=True,help='Locally inspected Android config JSON')
    ap.add_argument('--app',choices=['chatgpt','gemini','both'],default='both')
    ap.add_argument('--cases',default='',help='Comma-separated case IDs; default all 19')
    ap.add_argument('--repeats',type=int,default=1,help='New independent run of each case, default 1')
    ap.add_argument('--output',help='Output directory; existing data requires --resume')
    ap.add_argument('--catalog',help='Independent extension catalog; original 19-case CSV stays unchanged')
    ap.add_argument('--resume',action='store_true')
    ap.add_argument('--rerun-errors',action='store_true',help='On resume rerun ERROR cases, preserving attempts')
    a=ap.parse_args(argv)
    s=run_live(a.config,a.app,a.cases or None,a.repeats,a.output,a.resume,a.rerun_errors,catalog_path=a.catalog)
    print(json.dumps(s,indent=2))

if __name__=='__main__':
    main()
