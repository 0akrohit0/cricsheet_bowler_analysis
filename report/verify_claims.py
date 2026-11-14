"""Check every fixed (not data-generated) claim in the two reports against analysis/outputs/factor_results_<N>.json.
Prints one line per claim and exits with status 1 if any fails, so run_all.sh stops before a report goes out
saying something the new data no longer supports. When a claim fails, reword it in report/src (or make it
data-driven in build_plain.py / report_app.js) rather than loosening the check.
Usage, from the project folder: python report/verify_claims.py [N]   (default 100)"""
import json, os, sys
import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
D = json.load(open(os.path.join(PROJECT, 'analysis', 'outputs', f'factor_results_{N}.json')))

split = {r['component']: r for r in D['split_half']}
pred = {r['features']: r for r in D['prediction']}
fit = {r['model']: r for r in D['model_fit']}
effects = D['effects']
rel = lambda c: split[c]['reliability']
pred_includes_zero = lambda c: split[c]['pred_lo'] <= 0 <= split[c]['pred_hi']
eff = lambda v, l, t: next(e for e in effects if e['variable'] == v and e['level'] == l and e['bowler_type'] == t)
clear = lambda e: e['avg_lo'] > 0 or e['avg_hi'] < 0

def spread(var, t):
    """Share-weighted sd of a variable's level effects for one bowler type: how much it typically moves an average."""
    rows = [e for e in effects if e['variable'] == var and e['bowler_type'] == t]
    w = np.array([e['share'] for e in rows]); v = np.array([e['avg_pct'] for e in rows])
    w = w / w.sum()
    return float(np.sqrt((w * (v - (w * v).sum()) ** 2).sum()))

SITUATIONAL = ['wkt vs new batter (<10 balls)', 'wkt vs new ball (<15 overs)', 'wkt vs top order (1-4)',
               'wkt vs late in spell (over 6+)', 'wkt vs at home', 'wkt vs after 3+ dots']
STYLE = ['wides+no-balls per 100', '% bowled or lbw', '% caught by keeper']
DEALT_VARS = ['lineup', 'home_x_type', 'country_x_type', 'partner', 'era', 'umpire_lbw', 'toss_field',
              'innings_x_type', 'day_x_type', 'type']
wkt_sd = np.std([b['wicket-taking skill'] for b in D['bowlers']])
run_sd = np.std([b['run-control skill'] for b in D['bowlers']])
r2_profile = pred['profile (type, arm, age, era, white-ball record)']['LOO R² for 2nd-half average']
era_max = max(abs(e['avg_pct']) for e in effects if e['variable'] == 'era')

CLAIMS = [
    # (where, claim as written, holds?, evidence)
    ('both', 'The skill that repeats is run control, not wicket-taking',
     rel('run-control skill') > rel('wicket-taking skill') and split['run-control skill']['rel_lo'] > 0,
     f"run-control {rel('run-control skill'):.2f} (lo {split['run-control skill']['rel_lo']:.2f}) vs wicket-taking {rel('wicket-taking skill'):.2f}"),
    ('plain', 'Bowlers who take more wickets than expected early on usually don\'t keep doing so',
     rel('wicket-taking skill') < 0.2, f"wicket-taking reliability {rel('wicket-taking skill'):.2f} < 0.20"),
    ('both', 'Wicket-taking drives most of the visible spread', wkt_sd > run_sd,
     f'sd across bowlers: wicket-taking {wkt_sd:.3f} vs run-control {run_sd:.3f}'),
    ('both', 'Run control is the most reliable sign of quality (repeats at least as well as overall skill)',
     rel('run-control skill') >= rel('overall skill'), f"run-control {rel('run-control skill'):.2f} vs overall {rel('overall skill'):.2f}"),
    ('both', 'Situational "skills" that carry over at all do so less than run control',
     all(rel(c) < rel('run-control skill') for c in SITUATIONAL), ', '.join(f'{c[7:]} {rel(c):.2f}' for c in SITUATIONAL)),
    ('technical', 'Wides/no-balls, share bowled or lbw and share caught by the keeper are stable traits',
     all(rel(c) > 0.3 for c in STYLE), ', '.join(f'{c} {rel(c):.2f}' for c in STYLE)),
    ('both', '... but none of them predicts the average (no-balls "yet it doesn\'t predict")',
     all(pred_includes_zero(c) for c in STYLE),
     ', '.join(f"{c} [{split[c]['pred_lo']:.2f}, {split[c]['pred_hi']:.2f}]" for c in STYLE)),
    ('plain', 'No-balls and wides are "very consistent"', rel('wides+no-balls per 100') >= 0.5,
     f"reliability {rel('wides+no-balls per 100'):.2f} >= 0.50"),
    ('both', "Umpires' LBW rates in other matches make no measurable difference",
     not any(clear(e) and abs(e['avg_pct']) >= 2 for e in effects if e['variable'] == 'umpire_lbw'),
     ', '.join(f"{e['level']} {e['bowler_type']} {e['avg_pct']:+.1f}% [{e['avg_lo']:+.1f}, {e['avg_hi']:+.1f}]"
               for e in effects if e['variable'] == 'umpire_lbw' and e['bowler_type'] == 'pace')),
    ('both', 'Profile (type, arm, age, era, white-ball record) predicts little of the second-half average',
     r2_profile < 0.1, f'LOO R² {r2_profile:.3f} < 0.10'),
    ('technical', 'The additive model predicts as well as gradient boosting',
     fit['additive GLM (used)']['wicket log-loss'] <= 1.01 * fit['gradient boosting']['wicket log-loss'],
     f"wicket log-loss {fit['additive GLM (used)']['wicket log-loss']:.4f} vs {fit['gradient boosting']['wicket log-loss']:.4f} (within 1%)"),
    ('plain', 'For each type, the biggest condition is the line-up or the country, and the line-up is in the top two',
     all(max(spread('lineup', t), spread('country_x_type', t)) >= max(spread(v, t) for v in DEALT_VARS)
         and sorted((spread(v, t) for v in DEALT_VARS), reverse=True).index(spread('lineup', t)) < 2 for t in ('pace', 'spin')),
     '; '.join(t + ': ' + ', '.join(f'{v} {spread(v, t):.1f}' for v in DEALT_VARS) for t in ('pace', 'spin'))),
    ('plain', 'Weak and strong line-ups are shown in the conditions chart (effects clear)',
     clear(eff('lineup', '[28.0, 31.0)', 'pace')) and clear(eff('lineup', '[46.0, inf)', 'pace')), 'both intervals exclude 0'),
    ('plain', 'Era moves typical-conditions averages by a few percent at most', era_max <= 5, f'max |era effect| {era_max:.1f}% (<= 5)'),
]

failed = 0
for where, claim, ok, evidence in CLAIMS:
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'}  [{where}] {claim}\n        {evidence}")
print(f'\n{len(CLAIMS) - failed} of {len(CLAIMS)} claims hold')
sys.exit(1 if failed else 0)
