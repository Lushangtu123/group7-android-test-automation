"""Concretize reviewed Input × Context × Output coordinates; no remote LLM."""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from .augmentation import export_generated_cases

SELECTED = ('GEN-001', 'GEN-008', 'GEN-009', 'GEN-013')
FIELDS = ('case_id','feature','requirements','complexity','oracle','conversations_json',
          'expected','requires_human_review','provenance')


def concretize(selected_ids=None):
    with TemporaryDirectory() as folder:
        candidates = {r['generated_id']:r for r in export_generated_cases(Path(folder)/'candidates.csv')}
    selected_ids = selected_ids or SELECTED
    if any(key not in SELECTED for key in selected_ids):
        raise ValueError('Coordinate has not received the explicit validity pre-review')
    definitions = {
        'GEN-001': ('Factual/Domain','verified geography fact','new independent chat','verified answer',
            [['Name the capital city of Canada. Answer with the city name only.']], 'ottawa',
            'Explicitly identify Ottawa as the capital of Canada. Contradicted or merely quoted city mentions do not pass.',
            'A verified country/capital parameter in a fresh chat directly supports the requested verified-answer output.'),
        'GEN-008': ('Memory','preference statement','one interruption','recall original',
            [['My favorite animal is a dog. Remember this during our conversation.',
              'What is 8 + 6? Give only the number.',
              'Which animal did I tell you is my favorite? Give only the animal name.']], 'opt_memory_dog14',
            'Keep one conversation, calculate 8+6=14 during one interruption, then explicitly recall dog without inventing a changed preference.',
            'An explicit original preference plus exactly one intervening question makes recall of the original value testable.'),
        'GEN-009': ('NLU','clear question','standalone','clear semantic answer',
            [['Translate this sentence into French: The cat is sleeping. Reply with only the French sentence.']], 'opt_translate_fr_cat',
            'Give a complete affirmative French translation preserving cat and sleeping. Le chat dort and Le chat est en train de dormir are predeclared valid forms; explicit dog or negated sleep forms fail. Other wording requires REVIEW.',
            'An unambiguous standalone translation request tests natural-language understanding with whole-sentence semantic assertions, not keyword presence.'),
        'GEN-013': ('Fixed Flow','preference','five-turn original','correct intermediate steps',
            [['My favorite animal is a dog. Remember this during our conversation.',
              'What is 8 + 6? Give only the number.',
              'Define a parameterless Python function that prints Hello. Return only the function definition.',
              'What is the capital city of Australia? Give only the city name.',
              'What is my favorite animal? Give only the animal name.']], 'opt_flow_dog14_canberra',
            'Complete all five turns in one chat: original dog preference; 14; syntactically valid parameterless Hello-printing function; Canberra; dog recall. Never execute model-generated code.',
            'The five-step original flow structure is preserved with new dog/14/Australia parameters. Intermediate and final results have independent assertions.'),
    }
    result=[]
    for key in selected_ids:
        row=candidates[key];feature,input_class,context,output,groups,oracle,expected,reason=definitions[key]
        if (row['feature'],row['input_class'],row['context_class'],row['expected_output_class']) != (feature,input_class,context,output):
            raise ValueError('Reviewed coordinate no longer matches the generator taxonomy')
        result.append({**row,'case_id':'MB-'+key,'conversations':groups,'oracle':oracle,'expected':expected,
            'validity_pre_review':'CODEX_AI_LOGICAL_PRE_REVIEW','validity_reason':reason,
            'human_reviewer':'','human_approval':'','human_review_date':'',
            'generation_method':'Existing deterministic Cartesian generator followed by a reviewed coordinate-to-prompt template; no remote LLM call'})
    return result


def export_executable(path):
    rows=concretize();path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=FIELDS);writer.writeheader()
        for row in rows:
            writer.writerow({'case_id':row['case_id'],'feature':row['feature'],'requirements':'MODEL_BASED_EXTENSION',
                'complexity':'High' if len(row['conversations'][0])>1 else 'Low','oracle':row['oracle'],
                'conversations_json':json.dumps(row['conversations'],ensure_ascii=False),'expected':row['expected'],
                'requires_human_review':'YES' if row['oracle']=='manual_clarity' else 'NO',
                'provenance':'Optimization extension of '+row['generated_id']+'; outside formal114'})
    return rows
