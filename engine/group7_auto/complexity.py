"""Reproducible source-only script complexity: AST-based approximate cyclomatic complexity."""
import ast,csv
from pathlib import Path
from .catalog import ROOT

def calculate():
    rows=[]
    for file in sorted((ROOT/'group7_auto').glob('*.py')):
        code=file.read_text(encoding='utf-8')
        tree=ast.parse(code)
        lines=len(code.splitlines())
        functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        decisions=(ast.If,ast.For,ast.While,ast.ExceptHandler,ast.IfExp,ast.Assert,ast.Match)
        for f in functions:
            branches=sum(1 for n in ast.walk(f) if isinstance(n,decisions))
            branches+=sum(max(0,len(n.values)-1) for n in ast.walk(f) if isinstance(n,ast.BoolOp))
            rows.append({'module':file.name,'function':f.name,'start_line':f.lineno,'function_loc':f.end_lineno-f.lineno+1,'approx_cyclomatic_complexity':1+branches,'module_loc':lines,'metric_note':'AST branch count; not validated McCabe tool output'})
    return rows

def export(out):
    rows=calculate();out.parent.mkdir(exist_ok=True,parents=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return rows
