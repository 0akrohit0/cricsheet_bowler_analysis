"""Run the analysis cells in analysis/cells/ in order, in one namespace, and write
analysis/outputs/factor_results_<N>.json. A cell whose last statement is an expression has that value printed,
so the log shows the tables each step produces.
Usage, from the project folder: python analysis/scripts/run_analysis.py [N]
N overrides WICKET_WINDOW in 01_setup.py (default 100: bowlers with 100+ Test wickets, over their first 100)."""
import ast, os, sys, time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
CELLS = sorted((HERE.parent / 'cells').glob('[0-9][0-9]_*.py'))

N = int(sys.argv[1]) if len(sys.argv) > 1 else None

pd.set_option('display.max_rows', 200)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

def source(path):
    src = path.read_text()
    if path.name == '01_setup.py' and N is not None:
        assert 'WICKET_WINDOW = 100 ' in src, 'WICKET_WINDOW line not found in 01_setup.py'
        src = src.replace('WICKET_WINDOW = 100 ', f'WICKET_WINDOW = {N} ')
    return src

os.chdir(PROJECT)                    # the cells use paths relative to the project folder
namespace = {'__name__': '__main__'}
for path in CELLS:
    print(f'\n## {path.name}', flush=True)
    t0 = time.time()
    tree = ast.parse(source(path), filename=str(path))
    last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    exec(compile(tree, str(path), 'exec'), namespace)
    if last is not None:
        value = eval(compile(ast.Expression(last.value), str(path), 'eval'), namespace)
        if value is not None:
            print(value)
    print(f'## {path.name} done in {time.time() - t0:.0f}s', flush=True)
