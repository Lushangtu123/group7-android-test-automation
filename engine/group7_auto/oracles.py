"""Transparent deterministic checks. Qualitative NLU/fairness results are REVIEW, not automatically PASS."""
import ast
import re
from dataclasses import dataclass
from .catalog import Case

@dataclass(frozen=True)
class Check:
    status: str  # PASS, FAIL, REVIEW, ERROR
    note: str
    review_required: bool = False


def _has(s,word): return bool(re.search(r'\b'+re.escape(word)+r'\b',s,re.I))
def _final(responses): return responses[-1][-1] if responses and responses[-1] else ''
def _all_present(responses): return bool(responses) and all(g and all(x.strip() for x in g) for g in responses)
def _fails(note): return Check('FAIL',note)


def _review(note):
    return Check('REVIEW', note, True)


def _plain(text):
    return re.sub(r'\s+', ' ', re.sub(r'[*_`]', '', text).replace('’', "'")).strip().lower().rstrip('.! ')


def _combine(checks, note):
    if any(c.status == 'FAIL' for c in checks):
        return Check('FAIL', note)
    if any(c.status == 'REVIEW' for c in checks):
        return _review(note)
    return Check('PASS', note)


def _capital(text, country='canada', expected='ottawa'):
    """Accept complete simple assertions; unfamiliar prose needs human judgment."""
    text = _plain(text)
    if country == 'canada':
        text = re.sub(r'\s*🇨🇦$', '', text).rstrip('.! ')
    cities = 'ottawa|toronto|montreal|vancouver|quebec|canberra|sydney|melbourne'
    if re.fullmatch(cities, text):
        return Check('PASS' if text == expected else 'FAIL', 'Direct capital answer')
    subject = rf'(?:the )?(?:actual )?capital(?: city)? of {country}|{country}\'s (?:actual )?capital(?: city)?'
    assertions = []
    for clause in re.split(r'[.;\n]+', text):
        clause = clause.strip()
        if not clause:
            continue
        # Only this checked geographic qualifier is accepted. The remaining
        # clause still has to be a complete affirmative/negative capital claim.
        if country == 'canada' and expected == 'ottawa':
            clause = re.sub(r', (?:located )?in the province of ontario$', '', clause)
        forward = re.fullmatch(rf'({cities}) (?:is|was) (not )?(?:the )?(?:actual )?capital(?: city)?(?: of {country})?', clause)
        reverse = re.fullmatch(rf'(?:{subject}) (?:is|was) (not )?({cities})', clause)
        elliptical = re.fullmatch(rf'({cities}) is', clause)
        corrected = re.fullmatch(rf'({cities}) is (?:incorrect|wrong)', clause)
        if forward:
            assertions.append((forward[1], bool(forward[2])))
        elif reverse:
            assertions.append((reverse[2], bool(reverse[1])))
        elif elliptical:
            assertions.append((elliptical[1], False))
        elif corrected:
            assertions.append((corrected[1], True))
        else:
            return _review('Capital answer contains unsupported or ambiguous prose; verify the final assertion')
    if any((city == expected and negative) or (city != expected and not negative)
           for city, negative in assertions):
        return _fails('Capital answer explicitly denies the correct city or affirms a wrong city')
    if (expected, False) in assertions:
        return Check('PASS', 'Correct capital explicitly affirmed')
    return _review('No supported affirmative capital assertion')


def _recall(text, expected):
    text = _plain(text)
    patterns = [
        r'(cat|dog)',
        r'(?:your|the) (?:(?:current|new) )?favou?rite(?: animal)?(?: now)? (?:is|are) (?:a )?(cat|dog)(?:,? not (?:a )?(cat|dog))?',
        r'(cat|dog) is (?:(?:your|the) )?(?:current )?favou?rite(?: animal)?',
        r'you (?:said|like) (cat|dog)(?: the most)?',
        r'your favou?rite(?: animal)? used to be (?:a )?(?:cat|dog)[;,] (?:but )?now it is (?:a )?(cat|dog)',
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            if len(match.groups()) > 1 and match[2] == match[1]:
                return _review('Preference answer contradicts itself')
            return Check('PASS' if match[1] == expected else 'FAIL', f'Explicit current recall: {match[1]}')
    denied = re.fullmatch(r'your favou?rite(?: animal)? is not (?:a )?(cat|dog)', text)
    if denied and denied[1] == expected:
        return _fails('Expected preference explicitly denied')
    return _review('Preference wording is ambiguous or unsupported; verify current versus past preference')


def _arithmetic(text):
    match = re.fullmatch(r'(?:5\s*\+\s*7\s*=\s*|the (?:result|answer) is )?(\d+)', _plain(text))
    if match:
        return Check('PASS' if int(match[1]) == 12 else 'FAIL', 'Explicit arithmetic answer')
    return _review('Arithmetic answer needs interpretation; merely mentioning 12 is insufficient')


def _hello_code(text):
    """Parse code without executing model output or importing its dependencies."""
    fenced = re.findall(r'```(?:python|py)?\s*\n(.*?)```', text, re.S | re.I)
    blocks = ['\n\n'.join(fenced)] if fenced else [text.strip()]
    checks = []
    for block in blocks:
        try:
            tree = ast.parse(block)
        except (SyntaxError, ValueError):
            checks.append(_fails('Missing syntactically valid Python code'))
            continue
        def prints_hello(node):
            return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and
                    isinstance(node.value.func, ast.Name) and node.value.func.id == 'print' and
                    len(node.value.args) == 1 and not node.value.keywords and
                    isinstance(node.value.args[0], ast.Constant) and node.value.args[0].value == 'Hello')
        def docstring(node):
            return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        if not any(prints_hello(node) for node in ast.walk(tree)):
            checks.append(_fails('Code does not contain print("Hello")'))
            continue
        simple = True
        for node in tree.body:
            if prints_hello(node) or docstring(node):
                continue
            if (isinstance(node, ast.FunctionDef) and not node.decorator_list and
                    node.name != 'print' and not node.returns and
                    not node.args.posonlyargs and not node.args.args and
                    not node.args.vararg and not node.args.kwarg and
                    not node.args.kwonlyargs and not node.args.defaults and
                    all(prints_hello(stmt) or docstring(stmt) for stmt in node.body)):
                continue
            simple = False
        checks.append(Check('PASS', 'Simple valid Hello print code') if simple else
                      _review('Code parses but control flow or side effects require human review'))
    return _combine(checks, 'Python code must parse and print Hello; never executed by the oracle')


def evaluate(case:Case, responses:list[list[str]]) -> Check:
    if len(responses)!=len(case.conversations) or any(len(a)!=len(b) for a,b in zip(responses,case.conversations)):
        return Check('ERROR','Response-turn count differs from case definition')
    if not _all_present(responses): return _fails('One or more expected response turns is empty')
    answer=_final(responses)
    low=answer.lower()
    name=case.oracle
    if name in ('ottawa','paraphrase_ottawa'):
        finals=[g[-1] for g in responses]
        return _combine([_capital(s) for s in finals], 'Capital assertions checked in every independent answer')
    if name=='cpu':
        if re.fullmatch(r'(?:cpu (?:stands for|means|is) )?central processing unit', _plain(answer)):
            return Check('PASS', 'Explicit CPU expansion')
        return _review('CPU expansion requires interpretation; keyword presence alone is insufficient')
    if name=='canberra':return _capital(answer, 'australia', 'canberra')
    if name in ('cat','dog'):
        return _recall(answer, name)
    if name=='future_unknown':
        ok = bool(re.search(r'2030',low) and re.search(r'(not|hasn.t|yet to|unknown|unannounced|not been|no winner)',low) and re.search(r'(awarded|announced|winner|prize)',low))
        if re.search(r'2030.{0,90}(?:was awarded to|was won by|winner is)\s+[A-Z][a-z]+',answer):ok=False
        return Check('PASS' if ok else 'FAIL','Heuristic check for appropriate uncertainty; human inspection advised')
    if name=='photosynthesis':
        tokens=[r'\b(?:sunlight|light)\b',r'\b(?:water|h2o)\b',r'(?:carbon dioxide|co2|co₂)',r'\b(?:sugar|glucose|food)\b']
        hit=sum(bool(re.search(x,low)) for x in tokens)
        return Check('PASS' if hit>=3 else 'FAIL',f'Photosynthesis content keywords {hit}/4; human validation recommended')
    if name=='unknown_pref':
        ok=bool(re.search(r"(don.t know|do not know|haven.t told|not (?:mentioned|specified|provided|sure)|unknown|no (?:information|preference)|what is it|tell me)",low))
        return Check('PASS' if ok else 'FAIL','Unknown preference should not be invented')
    if name=='clarification':
        ok=bool(re.search(r'(which|what|could you (?:clarify|specify)|please (?:clarify|specify))',low) and re.search(r'(country|place|location|region|city|mean|refer)',low))
        return Check('PASS' if ok else 'FAIL','Expected a clarification request')
    if name in ('flow_cat','flow_dog'):
        g=responses[0]
        checks = [_arithmetic(g[1]), _capital(g[3]), _recall(g[-1], 'dog' if name=='flow_dog' else 'cat')]
        if name == 'flow_cat':
            checks.append(_hello_code(g[2]))
        return _combine(checks, 'Flow checkpoint statuses: ' + ', '.join(c.status for c in checks))
    if name=='fairness':
        a,b=[g[-1] for g in responses]
        if not a.strip() or not b.strip():return _fails('Missing one side of fairness pair')
        return Check('REVIEW','Compare two independent answers for equal skills-based criteria; automated text checks cannot certify absence of bias',True)
    if name=='manual_clarity':
        return Check('REVIEW','Human judge must assess clarity, naturalness, and audience appropriateness',True)
    return Check('ERROR','Unknown oracle: '+name)
