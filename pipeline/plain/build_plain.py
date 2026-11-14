"""Build the plain-language report 'Behind the Bowling Average' from both results files.

Every number on the page comes from factor_results.json (first 50 wickets) or factor_results_100.json
(first 100 wickets). Charts are plain HTML/CSS so they read at rest, scale to phone width and follow the theme.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
A = json.load(open(os.path.join(PROJECT, 'factor_results.json')))       # first 50 wickets
B = json.load(open(os.path.join(PROJECT, 'factor_results_100.json')))   # first 100 wickets
BASE = 30.0   # the illustrative "typical" bowler used to turn % effects into runs per wicket


def signal(d, k='share of variance that is real'):
    return next(r for r in d['signal'] if r['quantity'] == 'actual average')[k]

def share(d, part):
    return next(r for r in d['variance_shares'] if r['part'] == part)['share of real variance']

def split(d, comp, k='reliability'):
    return next(r for r in d['split_half'] if r['component'] == comp)[k]

def effect(v, level, t):
    return next(r for r in A['effects'] if r['variable'] == v and r['level'] == level and r['bowler_type'] == t)

def bowler(d, name):
    return next(b for b in d['bowlers'] if b['bowler'] == name)

pct = lambda x: f'{round(100 * x)}%'
esc = html.escape


# ---- chart 1: luck vs real -------------------------------------------------------------------
def luck_bar(d, label):
    real = signal(d)
    return f'''
    <div class="split-row">
      <div class="split-label">{label}</div>
      <div class="split-bar" role="img" aria-label="{label}: {pct(1 - real)} luck, {pct(real)} real differences">
        <div class="seg luck" style="flex:{1 - real:.3f}"><span>Luck {pct(1 - real)}</span></div>
        <div class="seg real" style="flex:{real:.3f}"><span>Real {pct(real)}</span></div>
      </div>
    </div>'''


# ---- chart 2: where the real differences come from ----------------------------------------------
PARTS = [('baseline (pace or spin)', 'Pace or spin', 'p-type'), ('dealt', 'Conditions they were given', 'p-dealt'),
         ('shaped', 'Match situations', 'p-shaped'), ('bowler_effect', 'The bowler', 'p-bowler')]

def sources_bar(d, label):
    vals = [max(0.0, share(d, k)) for k, _, _ in PARTS]
    tot = sum(vals)
    segs = ''.join(
        f'<div class="seg {cls}" style="flex:{v / tot:.3f}" title="{name}: {pct(v / tot)}"><span>{pct(v / tot)}</span></div>'
        for (k, name, cls), v in zip(PARTS, vals))
    desc = ', '.join(f'{name} {pct(v / tot)}' for (k, name, cls), v in zip(PARTS, vals))
    return f'''
    <div class="split-row">
      <div class="split-label">{label}</div>
      <div class="split-bar" role="img" aria-label="{label}: {desc}">{segs}</div>
    </div>'''


# ---- chart 3: what a 30-average bowler would average in each condition --------------------------
CONDITIONS = [
    ('Who they bowl at', [
        ('Facing a weak batting line-up', 'top seven averaging 28 to 31', effect('lineup', '[28.0, 31.0)', 'pace')),
        ('Facing a strong batting line-up', 'top seven averaging 46 or more', effect('lineup', '[46.0, inf)', 'pace')),
    ]),
    ('Home or away', [
        ('Playing at home', 'fast bowlers; spinners are similar', effect('home_x_type', 'home', 'pace')),
        ('Playing away', 'fast bowlers; spinners are similar', effect('home_x_type', 'away', 'pace')),
    ]),
    ('The bowler at the other end', [
        ('A strong partner', 'partner averaging under 26', effect('partner', '[0.0, 26.0)', 'pace')),
        ('A weak partner', 'partner averaging 38 or more', effect('partner', '[38.0, inf)', 'pace')),
    ]),
    ('Where spinners bowl', [
        ('Spinner in India', '', effect('country_x_type', 'India', 'spin')),
        ('Spinner in Australia', '', effect('country_x_type', 'Australia', 'spin')),
    ]),
    ('Where fast bowlers bowl', [
        ('Fast bowler in South Africa', '', effect('country_x_type', 'South Africa', 'pace')),
        ('Fast bowler in Sri Lanka', '', effect('country_x_type', 'Sri Lanka', 'pace')),
    ]),
]
MAX_DELTA = 7.0   # runs either side of 30 that the bar track spans

def condition_rows():
    out = []
    for group, rows in CONDITIONS:
        out.append(f'<div class="cond-group">{esc(group)}</div>')
        for name, note, e in rows:
            avg = BASE * (1 + e['avg_pct'] / 100)
            delta = avg - BASE
            width = min(abs(delta), MAX_DELTA) / MAX_DELTA * 50
            side = 'better' if delta < 0 else 'worse'
            pos = f'right:50%;width:{width:.1f}%' if delta < 0 else f'left:50%;width:{width:.1f}%'
            words = f'{abs(delta):.1f} runs {"cheaper" if delta < 0 else "dearer"} per wicket'
            out.append(f'''
      <div class="cond-row">
        <div class="cond-name">{esc(name)}{f'<small>{esc(note)}</small>' if note else ''}</div>
        <div class="cond-track" role="img" aria-label="{esc(name)}: average {avg:.1f}, {words}">
          <div class="cond-mid"></div>
          <div class="cond-bar {side}" style="{pos}"></div>
        </div>
        <div class="cond-value"><b>{avg:.1f}</b><small>{words}</small></div>
      </div>''')
    return ''.join(out)


# ---- chart 4: does it carry over? ------------------------------------------------------------------
def carry_rows():
    out = []
    for comp, name, note in [('run-control skill', 'Keeping runs down', 'conceding fewer runs than the conditions predict'),
                             ('wicket-taking skill', 'Taking wickets often', 'taking more wickets than the conditions predict')]:
        bars = ''
        for d, lab, cls in [(A, 'First 50 wickets', 'w50'), (B, 'First 100 wickets', 'w100')]:
            v = split(d, comp)
            shown = max(0.0, v)
            txt = f'{v:.2f}'.replace('-', '−') if v >= 0.05 else 'none'
            bars += f'''
          <div class="carry-bar-row">
            <span class="carry-win">{lab}</span>
            <div class="carry-track" role="img" aria-label="{name}, {lab}: carry-over {txt}"><div class="carry-bar {cls}" style="width:{shown * 100:.0f}%"></div></div>
            <span class="carry-val">{txt}</span>
          </div>'''
        out.append(f'<div class="carry-item"><div class="carry-name">{name}<small>{note}</small></div><div class="carry-bars">{bars}</div></div>')
    return ''.join(out)


# ---- chart 5: actual vs expected for well-known bowlers (first 100 wickets) -------------------------
NAMES = [('VD Philander', 'Vernon Philander'), ('PJ Cummins', 'Pat Cummins'), ('K Rabada', 'Kagiso Rabada'),
         ('JJ Bumrah', 'Jasprit Bumrah'), ('RA Jadeja', 'Ravindra Jadeja'), ('R Ashwin', 'Ravichandran Ashwin'),
         ('NM Lyon', 'Nathan Lyon'), ('SCJ Broad', 'Stuart Broad'), ('RAS Lakmal', 'Suranga Lakmal')]
LO, HI = 15, 45

def x(v):
    return (min(max(v, LO), HI) - LO) / (HI - LO) * 100

def bowler_rows():
    out = []
    for key, full in NAMES:
        b = bowler(B, key)
        a, e = b['actual'], b['xAvg']
        diff = a - e
        cls = 'better' if diff < 0 else 'worse'
        left, right = sorted([x(a), x(e)])
        verdict = f'{abs(diff):.1f} runs {"better" if diff < 0 else "worse"} than expected'
        out.append(f'''
      <div class="bw-row">
        <div class="bw-name">{esc(full)}<small>{b['tests']} Tests · {b['bowler_type']}</small></div>
        <div class="bw-track" role="img" aria-label="{esc(full)}: expected {e:.1f}, actual {a:.1f}, {verdict}">
          <div class="bw-line {cls}" style="left:{left:.1f}%;width:{right - left:.1f}%"></div>
          <div class="bw-dot expected" style="left:{x(e):.1f}%" title="Expected {e:.1f}"></div>
          <div class="bw-dot actual {cls}" style="left:{x(a):.1f}%" title="Actual {a:.1f}"></div>
        </div>
        <div class="bw-value"><b>{a:.1f}</b><small>{verdict}</small></div>
      </div>''')
    ticks = ''.join(f'<span style="left:{x(t):.1f}%">{t}</span>' for t in range(LO, HI + 1, 5))
    out.append(f'<div class="bw-row bw-axis"><div></div><div class="bw-ticks">{ticks}</div><div></div></div>')
    return ''.join(out)


# ---- numbers used in the prose --------------------------------------------------------------------
olivier = bowler(A, 'D Olivier')
values = {
    'n_tests': A['meta']['n_tests'],
    'n_balls': f"{A['meta']['n_deliveries_model'] / 1e6:.1f} million",
    'n_bowlers_model': A['meta']['n_bowlers_model'],
    'n50': A['meta']['n_bowlers'], 'n100': B['meta']['n_bowlers'],
    'luck50': pct(1 - signal(A)), 'luck100': pct(1 - signal(B)),
    'rel_raw50': f"{A['meta']['raw_half_reliability'][0]:.2f}", 'rel_raw100': f"{B['meta']['raw_half_reliability'][0]:.2f}",
    'dealt50': pct(share(A, 'dealt')), 'dealt100': pct(share(B, 'dealt')),
    'bowler50': pct(share(A, 'bowler_effect')), 'bowler100': pct(share(B, 'bowler_effect')),
    'shaped50': pct(share(A, 'shaped')), 'shaped100': pct(share(B, 'shaped')),
    'pace_base': f"{A['meta']['baseline_by_type']['pace']:.1f}", 'spin_base': f"{A['meta']['baseline_by_type']['spin']:.1f}",
    'run50': f"{split(A, 'run-control skill'):.2f}", 'run100': f"{split(B, 'run-control skill'):.2f}",
    'wkt50': f"{split(A, 'wicket-taking skill'):.2f}", 'wkt100': f"{split(B, 'wicket-taking skill'):.2f}".replace('-', '−'),
    'noball100': f"{split(B, 'wides+no-balls per 100'):.2f}",
    'oli_actual': f"{olivier['actual']:.1f}", 'oli_expected': f"{olivier['xAvg']:.1f}",
    'cummins_effect': f"{abs(bowler(B, 'PJ Cummins')['bowler_effect']):.1f}",
    'lyon_actual': f"{bowler(B, 'NM Lyon')['actual']:.1f}", 'lyon_expected': f"{bowler(B, 'NM Lyon')['xAvg']:.1f}",
    'lyon_effect': f"{bowler(B, 'NM Lyon')['bowler_effect']:.1f}".replace('-', '−'),
    'offspin_lhb': f"{abs(effect('bat_hand_x_type', 'opposite', 'spin')['avg_pct']):.0f}%",
    'spin4th': f"{abs(effect('innings_x_type', '4', 'spin')['avg_pct']):.0f}%",
    'luck_chart': luck_bar(A, 'First 50 wickets') + luck_bar(B, 'First 100 wickets'),
    'sources_chart': sources_bar(A, 'First 50 wickets') + sources_bar(B, 'First 100 wickets'),
    'conditions_chart': condition_rows(),
    'carry_chart': carry_rows(),
    'bowlers_chart': bowler_rows(),
}

page = open(os.path.join(HERE, 'template.html')).read()
for k, v in values.items():
    page = page.replace('{{' + k + '}}', str(v))
assert '{{' not in page, page[page.index('{{'):page.index('{{') + 40]

with open(os.path.join(HERE, 'Behind the Bowling Average.html'), 'w') as f:      # publish copy
    f.write(page)
standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + page.replace('<header', '</head>\n<body>\n<header', 1) + '\n</body>\n</html>\n')
with open(os.path.join(PROJECT, 'Behind the Bowling Average.html'), 'w') as f:
    f.write(standalone)
print('written', len(standalone) // 1024, 'KB')
