"""Assemble nb/*.py into 'Bowler Average Factors - First N.ipynb', execute it in a fresh kernel, and save outputs."""
import json, os, sys, time
from jupyter_client.manager import start_new_kernel

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
# Window size from the command line: 50 (main) or 100. The other one becomes the robustness check.
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
H, OTHER = N // 2, (100 if N == 50 else 50)
SUFFIX = f' - First {N}'
OUT = os.path.join(PROJECT, f'Bowler Average Factors{SUFFIX}.ipynb')
RESULTS = 'factor_results.json' if N == 50 else f'factor_results_{N}.json'

def code(name):
    src = open(os.path.join(HERE, 'nb', name)).read().strip('\n')
    if name == '01_setup.py':
        src = (src.replace('WICKET_WINDOW = 50 ', f'WICKET_WINDOW = {N} ')
                  .replace('SENSITIVITY_WINDOW = 100 ', f'SENSITIVITY_WINDOW = {OTHER} ')
                  .replace("RESULTS_FILE = 'factor_results.json'", f"RESULTS_FILE = '{RESULTS}'"))
    return ('code', src)

def md(text):
    return ('markdown', text.strip('\n').replace('{H1}', str(H + 1)).replace('{H}', str(H))
            .replace('{N}', str(N)).replace('{OTHER}', str(OTHER)))

CELLS = [
    md("""
# Which factors make a Test bowler's average low?

The earlier analysis (`Test Bowler Average Analysis.ipynb`) mostly restated the definition of the average:
average = strike rate × economy ÷ 6, and "removes batters before they're set" is runs conceded per wicket
in other words. This notebook asks the question in a way that can't be answered by arithmetic.

**Design rules**

1. **Context is valued from everyone else.** Each delivery gets a context-expected wicket probability and
   expected runs from models trained on every other bowler's deliveries (cross-fitted by bowler), using only
   things known before the ball is bowled.
2. **Skill claims must survive out of sample.** A trait measured on wickets 1–{H} only counts if it predicts
   how the bowler does on wickets {H1}–{N}.
3. **Mechanical stats (strike rate, economy, dots, maidens) are never explanatory features.**

**Scope:** international Tests only (Cricsheet `match_type == "Test"`, `team_type == "international"`, national
sides only), each bowler's **first {N} Test wickets** (core results repeated at {OTHER}), bowlers whose first Test in the data is on
or after 2007-01-01 so that wicket 1 really is their first.
"""),
    md("## 0. Setup"),
    code('01_setup.py'),
    md("""
## 1. Parse every international Test

One row per delivery, with the fields the old parser dropped: fielders, DRS reviews, toss, umpires, declarations
and the event name (used to find the host country). Parsed once and cached in `cache/`.
"""),
    code('02_parse.py'),
    md("""
## 2. Context for every delivery, known before it is bowled

- **Batter:** pre-match Test average (shrunk toward the batting position's norm) and strike rate, Tests played,
  batting position, hand, balls faced so far this innings.
- **Opposition line-up:** mean pre-match average of the batting side's best seven. This is fixed before the
  match. Which batter is at the crease is kept separate, because a bowler who removes the top order then bowls
  at the tail.
- **Ball and phase:** overs since the new ball (assumed taken at 80), innings 1–4, overs into the match (≈ day).
- **Match state:** bowling side's lead, wickets down, follow-on.
- **Venue:** host country from the event name ("India tour of Australia"), then from other events at the
  same ground; home / away / neutral for the bowler; UAE treated as neutral. Toss.
- **Era and officials:** year, whether DRS reviews were recorded, the umpires' LBW rate in *other* matches.
- **Role and usage:** opening the bowling, over number within the spell (a spell breaks after a gap of
  more than one over from that bowler), spell number, overs already bowled in the match.
- **Bowling partner:** the bowler at the other end and their pre-match average.
"""),
    code('03_ball_features.py'),
    md("## 3. Each bowler's first {N} Test wickets"),
    code('04_windows.py'),
    md("""
## 4. The context model

Two additive log-link GLMs on every Test delivery since 2007 (all 700-odd bowlers, not just the study bowlers):
probability of a bowler wicket, and expected bowler runs. Every variable is binned, and interactions with
pace/spin sit inside their own group. Fits are cross-fitted: a bowler's deliveries are always scored by models
that never saw that bowler.

The variables are grouped. **Dealt** groups are outside the bowler's control. **Shaped** groups are situations
that partly result from the bowler's (or team's) own success, or the captain's reading of it, so they are never
counted as luck.
"""),
    code('05_design.py'),
    md("""
The additive GLM is compared with gradient boosting on the same deliveries (out of fold). If boosting found
important interactions the GLM misses, it would win clearly. It doesn't, so the additive model's group terms
can be used for exact attribution. Ball-level outcomes are very noisy, so the % explained per ball is small
by nature; what matters is the sum over thousands of balls.
"""),
    code('06_models.py'),
    md("""
## 5. Attribution: how much of each bowler's average is context, and which context?

For every bowler, **xAvg** = expected runs ÷ expected wickets over their window, given everything in the context
model. Each group's contribution, in runs per wicket, is its **grouped Shapley value**: the average change in
xAvg from switching that group from typical conditions to the bowler's actual conditions, over all orders of
switching the others. "Typical" means the context of a random league delivery **by the same type of bowler**,
so spinners are compared with spinners. The log link makes that expectation exact, with no sampling.

`actual = baseline(pace or spin) + Σ dealt + Σ shaped + bowler effect`, and the code asserts that it adds up.
"""),
    code('07_attribution.py'),
    md("""
## 6. How much of the spread is just luck?

{N} wickets is a small sample. Resampling each bowler's Tests gives the sampling noise in every quantity.
Subtracting it shows how much of the spread in averages is real, and which parts that real spread comes from.
"""),
    code('08_uncertainty.py'),
    md("""
## 7. Bowler skill components, measured on each half of the window

All are context-adjusted: actual ÷ expected from the context model, on a log scale, oriented so that
**higher = better than the context predicts**, and shrunk toward zero (5 pseudo-wickets, 150 pseudo-runs).
"Overall skill" is exactly wicket-taking skill + run-control skill.
"""),
    code('09_skill.py'),
    md("""
## 8. The split-half test: which traits are real, and which predict?

- **Reliability:** does the trait in wickets 1–{H} match the same trait in wickets {H1}–{N}?
- **Predicts 2nd-half skill:** does the trait in wickets 1–{H} predict how much better than context the bowler is
  in wickets {H1}–{N}? There is no overlap in data, so this can't be circular.
"""),
    code('10_split_half.py'),
    md("""
## 9. Specific effects: how much does each condition move the average?

For each level of each context variable, the change in the average with everything else at typical conditions
for that bowler type, split into its strike-rate and economy parts. The 95% intervals come from refitting both
models on Tests resampled with replacement. These don't depend on the wicket window, so they are cached
in `cache/` after the first run.
"""),
    code('11_effects.py'),
    md("""
## 10. Predicting the second half

Ridge regression with leave-one-out predictions. Profile features include the bowler's record in ODIs and T20Is
before their Test debut (international white-ball matches only; no domestic cricket).
"""),
    code('12_prediction.py'),
    md("## 11. Robustness: pace only, spin only, and the first {OTHER} wickets"),
    code('13_sensitivity.py'),
    md("## 12. Figures"),
    code('14_figures.py'),
    md("## 13. Export for the report"),
    code('15_export.py'),
]


def run(cells):
    km, kc = start_new_kernel(kernel_name='python3', cwd=PROJECT)
    nb_cells, n = [], 0
    try:
        for kind, src in cells:
            if kind == 'markdown':
                nb_cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': src.splitlines(True)})
                continue
            n += 1
            t0 = time.time()
            msg_id = kc.execute(src)
            outputs = []
            while True:
                msg = kc.get_iopub_msg(timeout=7200)
                if msg['parent_header'].get('msg_id') != msg_id:
                    continue
                t, c = msg['msg_type'], msg['content']
                if t == 'stream':
                    if outputs and outputs[-1].get('output_type') == 'stream' and outputs[-1]['name'] == c['name']:
                        outputs[-1]['text'].append(c['text'])
                    else:
                        outputs.append({'output_type': 'stream', 'name': c['name'], 'text': [c['text']]})
                elif t in ('execute_result', 'display_data'):
                    o = {'output_type': t, 'data': c['data'], 'metadata': c.get('metadata', {})}
                    if t == 'execute_result':
                        o['execution_count'] = n
                    outputs.append(o)
                elif t == 'error':
                    outputs.append({'output_type': 'error', 'ename': c['ename'], 'evalue': c['evalue'],
                                    'traceback': c['traceback']})
                    print('\n'.join(c['traceback']))
                    raise SystemExit(f'cell {n} failed')
                elif t == 'status' and c['execution_state'] == 'idle':
                    break
            print(f'cell {n} ok ({time.time() - t0:.0f}s)', flush=True)
            nb_cells.append({'cell_type': 'code', 'execution_count': n, 'metadata': {}, 'outputs': outputs,
                             'source': src.splitlines(True)})
    finally:
        kc.stop_channels(); km.shutdown_kernel(now=True)
    return nb_cells


if __name__ == '__main__':
    cells = run(CELLS)
    nb = {'cells': cells, 'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                                       'language_info': {'name': 'python'}}, 'nbformat': 4, 'nbformat_minor': 5}
    with open(OUT, 'w') as f:
        json.dump(nb, f, indent=1)
    print('Wrote', OUT)
