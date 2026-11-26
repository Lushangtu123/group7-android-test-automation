"""Read and verify the Group 7 Deliverable #2 test catalog."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Case:
    case_id: str
    feature: str
    requirements: str
    complexity: str
    oracle: str
    conversations: list[list[str]]
    expected: str
    human_review: bool
    provenance: str


def load_cases(path: Path | None = None) -> list[Case]:
    path = Path(path or ROOT / 'data' / 'test_cases.csv')
    with path.open(encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    cases = []
    for row in rows:
        groups = json.loads(row['conversations_json'])
        if not isinstance(groups,list) or not groups or not all(isinstance(g,list) and g and all(isinstance(s,str) and s.strip() for s in g) for g in groups):
            raise ValueError(f"Invalid conversation groups: {row['case_id']}")
        cases.append(Case(row['case_id'],row['feature'],row['requirements'],row['complexity'],row['oracle'],groups,row['expected'],row['requires_human_review']=='YES',row['provenance']))
    ids = [c.case_id for c in cases]
    if len(set(ids))!=len(ids): raise ValueError('Duplicate test case IDs in test_cases.csv')
    return cases


def discover(cases: list[Case]) -> dict:
    known={'FR-A1','FR-A2','FR-A3','FR-M1','FR-M2','FR-M3','FR-N1','FR-N2','FR-N3','FR-N4','FR-F1','FR-F2','FR-F3','AR-U1','AR-H1','AR-R1','AR-B1','AR-C1'}
    mentioned={r for c in cases for r in c.requirements.split(';')}
    # AR-R1 maps via the natural-language robustness/typo test as defined in D#2.
    implied={'AR-R1'} if any(c.case_id=='TC-NLU-03' for c in cases) else set()
    missing=sorted(known-(mentioned|implied))
    unknown=sorted(mentioned-known)
    groups={k:sum(c.feature==k for c in cases) for k in sorted({c.feature for c in cases})}
    return {'source':'Group 7 Deliverable #2; manually transcribed checked prompts','case_count':len(cases), 'application_count_planned':2, 'planned_app_case_executions':len(cases)*2, 'case_ids_unique':True,'feature_counts':groups,'explicitly_mapped_requirements':sorted(mentioned),'implied_requirement_note':'AR-R1 robustness is covered by TC-NLU-03/02 via input rephrasing and typo cases.','missing_requirements':missing,'unknown_requirement_ids':unknown,'cases_requiring_human_review':[c.case_id for c in cases if c.human_review], 'data_discovery_scope':'Project CSV and classification taxonomy only; no personal account information downloaded.'}
