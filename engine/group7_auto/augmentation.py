"""Reproducible augmentation: reviewed seed examples and classification-based candidates.
Not a claim that a remote generative model has been executed.
"""
import csv,json,itertools
from pathlib import Path
from .catalog import ROOT


def export_augmentations(out:Path):
    src=ROOT/'data'/'augmentation_seed.csv'
    with src.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    for r in rows:
        r['generation_method']='AI-assisted authored seed; deterministic export (no live LLM call)'
        r['execution_status']='HISTORICAL_MANUAL_ONLY' if r['variant_id']=='AUG-05' else 'PROPOSED_NOT_RUN'
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return rows


def export_generated_cases(out:Path,limit_per_feature:int=4):
    taxonomy=json.loads((ROOT/'data'/'classification_model.json').read_text(encoding='utf-8'))
    rows=[]
    for feature,classes in taxonomy.items():
        for n,(i,c,o) in enumerate(itertools.product(classes['input'],classes['context'],classes['output'])):
            if n>=limit_per_feature:break
            rows.append({'generated_id':f'GEN-{len(rows)+1:03d}','feature':feature,'input_class':i,'context_class':c,'expected_output_class':o,'review_status':'CANDIDATE_NEEDS_LOGIC_REVIEW','execution_status':'NOT_EXECUTED'})
    out.parent.mkdir(exist_ok=True,parents=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return rows
