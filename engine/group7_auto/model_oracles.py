"""Separate extension oracles; the historical formal-test evaluator is unchanged."""
import re
from .oracles import Check, evaluate as original_evaluate, _plain, _recall, _capital, _hello_code, _combine


def arithmetic14(text):
    match=re.fullmatch(r'(?:8\s*\+\s*6\s*=\s*|the (?:result|answer) is )?(\d+)',_plain(text))
    if match:
        return Check('PASS' if int(match[1])==14 else 'FAIL','Explicit 8+6 answer')
    return Check('REVIEW','Arithmetic requires interpretation; the presence of 14 alone is insufficient',True)


def evaluate(case,responses):
    if not case.oracle.startswith('opt_'):
        return original_evaluate(case,responses)
    if len(responses)!=len(case.conversations) or any(len(a)!=len(b) for a,b in zip(responses,case.conversations)):
        return Check('ERROR','Extension response count differs from the declared conversation')
    if any(not answer.strip() for group in responses for answer in group):
        return Check('FAIL','Empty extension answer')
    group=responses[0]
    if case.oracle=='opt_translate_fr_cat':
        answer=_plain(group[0])
        if answer in ('le chat dort','le chat est en train de dormir'):
            return Check('PASS','Whole affirmative French translation matches a declared valid form')
        if answer in ('le chien dort','le chien est en train de dormir','le chat ne dort pas'):
            return Check('FAIL','Translation explicitly changes the animal or negates sleeping')
        return Check('REVIEW','Unfamiliar complete translation or additional prose requires semantic review',True)
    checks=[arithmetic14(group[1]),_recall(group[-1],'dog')]
    if case.oracle=='opt_flow_dog14_canberra':
        checks.extend([_hello_code(group[2]),_capital(group[3],'australia','canberra')])
    elif case.oracle!='opt_memory_dog14':
        return Check('ERROR','Unknown optimization oracle')
    return _combine(checks,'Extension checkpoint statuses: '+', '.join(check.status for check in checks))
