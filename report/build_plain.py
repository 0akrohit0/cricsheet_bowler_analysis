"""Build the plain-language report 'Behind the Bowling Average' from analysis/outputs/factor_results_<N>.json.

Every number on the page comes from the results file, and so does the wording of any claim whose direction depends
on the data (better/worse, which part matters most). The fixed claims that remain are checked by verify_claims.py.
Charts are plain HTML/CSS so they read at rest, scale to phone width and follow the theme.
Usage, from the project folder: python report/build_plain.py [N]   (default 100)
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
D = json.load(open(os.path.join(PROJECT, 'analysis', 'outputs', f'factor_results_{N}.json')))
M = D['meta']
BASE = 30.0   # the illustrative "typical" bowler used to turn % effects into runs per wicket


def signal(k='share of variance that is real'):
    return next(r for r in D['signal'] if r['quantity'] == 'actual average')[k]

def share(part):
    return next(r for r in D['variance_shares'] if r['part'] == part)['share of real variance']

def split(comp, k='reliability'):
    return next(r for r in D['split_half'] if r['component'] == comp)[k]

def effect(v, level, t):
    return next(r for r in D['effects'] if r['variable'] == v and r['level'] == level and r['bowler_type'] == t)

def clear(e):
    """The effect's 95% interval excludes zero."""
    return e['avg_lo'] > 0 or e['avg_hi'] < 0

def bowler(name):
    return next(b for b in D['bowlers'] if b['bowler'] == name)

def runs(pct_change):
    return BASE * pct_change / 100

pct = lambda x: f'{round(100 * x)}%'
num = lambda v, d=2: f'{v:.{d}f}'.replace('-', '−')
esc = html.escape


# ---- chart 1: luck vs real -------------------------------------------------------------------
def luck_bar(label):
    real = signal()
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

def display_share(part):
    """Share as displayed everywhere, matching the technical report. A part with a negative share (it narrows the gaps
    between bowlers instead of widening them) shows as ≈0% and is left off the bar."""
    return max(0.0, share(part))

negative = [n for k, n, _ in PARTS if share(k) < 0]
sources_sub = ('The bar shows the real (non-luck) differences. ' +
               (f"{' and '.join(negative)} came out {'close to' if all(share(k) > -0.10 for k, _, _ in PARTS) else 'below'} "
                f"zero, so the other {'three parts add' if len(negative) == 1 else 'parts add'} up to a little over 100%."
                if negative else 'It adds up to 100%.'))

display_pct = lambda part: '≈0%' if display_share(part) < 0.02 else pct(display_share(part))

def sources_bar(label):
    segs = ''.join(
        f'<div class="seg {cls}" style="flex:{display_share(k):.3f}" title="{name}: {display_pct(k)}"><span>{display_pct(k)}</span></div>'
        for k, name, cls in PARTS if display_share(k) > 0)
    desc = ', '.join(f'{name} {display_pct(k)}' for k, name, cls in PARTS)
    return f'''
    <div class="split-row">
      <div class="split-label">{label}</div>
      <div class="split-bar" role="img" aria-label="{label}: {desc}">{segs}</div>
    </div>'''


# ---- chart 3: what a 30-average bowler would average in each condition --------------------------
CONDITIONS = [
    ('Who they bowl at', [
        ('Facing a weak batting line-up', 'top seven averaging 28 to 31', ('lineup', '[28.0, 31.0)', 'pace')),
        ('Facing a strong batting line-up', 'top seven averaging 46 or more', ('lineup', '[46.0, inf)', 'pace')),
    ]),
    ('Home or away', [
        ('Fast bowler at home', '', ('home_x_type', 'home', 'pace')),
        ('Fast bowler away', '', ('home_x_type', 'away', 'pace')),
        ('Spinner at home', '', ('home_x_type', 'home', 'spin')),
        ('Spinner away', '', ('home_x_type', 'away', 'spin')),
    ]),
    ('The bowler at the other end', [
        ('A strong partner', 'partner averaging under 26', ('partner', '[0.0, 26.0)', 'pace')),
        ('A weak partner', 'partner averaging 38 or more', ('partner', '[38.0, inf)', 'pace')),
    ]),
    ('Where spinners bowl', [
        ('Spinner in India', '', ('country_x_type', 'India', 'spin')),
        ('Spinner in Sri Lanka', '', ('country_x_type', 'Sri Lanka', 'spin')),
        ('Spinner in Australia', '', ('country_x_type', 'Australia', 'spin')),
        ('Spinner in New Zealand', '', ('country_x_type', 'New Zealand', 'spin')),
    ]),
    ('Where fast bowlers bowl', [
        ('Fast bowler in West Indies', '', ('country_x_type', 'West Indies', 'pace')),
        ('Fast bowler in South Africa', '', ('country_x_type', 'South Africa', 'pace')),
        ('Fast bowler in Pakistan', '', ('country_x_type', 'Pakistan', 'pace')),
        ('Fast bowler in India', '', ('country_x_type', 'India', 'pace')),
    ]),
]
MAX_DELTA = 10.0   # runs either side of 30 that the bar track spans

def condition_rows():
    out = []
    for group, rows in CONDITIONS:
        shown = [(name, note, effect(*key)) for name, note, key in rows if clear(effect(*key))]
        if not shown:
            continue
        out.append(f'<div class="cond-group">{esc(group)}</div>')
        for name, note, e in shown:
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
        v = split(comp)
        txt = num(v) if v >= 0.05 else 'none'
        out.append(f'''<div class="carry-item"><div class="carry-name">{name}<small>{note}</small></div><div class="carry-bars">
          <div class="carry-bar-row">
            <span class="carry-win">Wickets {M['window'] // 2 + 1}–{M['window']}</span>
            <div class="carry-track" role="img" aria-label="{name}: carry-over {txt}"><div class="carry-bar w100" style="width:{max(0.0, v) * 100:.0f}%"></div></div>
            <span class="carry-val">{txt}</span>
          </div></div></div>''')
    return ''.join(out)


# ---- chart 5: actual vs expected for well-known bowlers ---------------------------------------------
NAMES = [('VD Philander', 'Vernon Philander'), ('PJ Cummins', 'Pat Cummins'), ('K Rabada', 'Kagiso Rabada'),
         ('JJ Bumrah', 'Jasprit Bumrah'), ('RA Jadeja', 'Ravindra Jadeja'), ('R Ashwin', 'Ravichandran Ashwin'),
         ('NM Lyon', 'Nathan Lyon'), ('SCJ Broad', 'Stuart Broad'), ('RAS Lakmal', 'Suranga Lakmal')]
SHOWN = [(key, full) for key, full in NAMES if any(b['bowler'] == key for b in D['bowlers'])]
FULL_NAME = dict(NAMES)

def display_name(b):
    """Readable name for a bowler outside the hand-picked list: the registry's alternative name with the fullest first
    name (e.g. 'P Jayasuriya' rather than 'NGRP Jayasuriya'), with the team in front."""
    if b['bowler'] in FULL_NAME:
        return FULL_NAME[b['bowler']]
    import csv
    alts = [r['name'] for r in csv.DictReader(open(os.path.join(PROJECT, 'data', 'names.csv'))) if r['identifier'] == b['bowler_id']]
    best = max([b['bowler']] + alts, key=lambda n: (len(n.split()[0]) if n.split()[0][1:].islower() else 0, -len(n)))
    if best.split()[0].isupper() and len(best.split()[0]) > 1:      # initials only: keep the shortest form
        best = min([b['bowler']] + alts, key=len)
    return f"{b['team']}'s {best}"
LO, HI = 15, 45

def x(v):
    return (min(max(v, LO), HI) - LO) / (HI - LO) * 100

def bowler_rows():
    out = []
    for key, full in SHOWN:
        b = bowler(key)
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

def join_names(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]

def bowlers_sentence():
    rows = [(full, bowler(key)['bowler_effect']) for key, full in SHOWN]
    best = min(rows, key=lambda r: r[1])
    worse = [full for full, e in rows if e > 0]
    s = f'{best[0]} beat what his conditions would predict by {abs(best[1]):.1f} runs per wicket, the most of the bowlers shown.'
    if worse:
        s += f' {join_names(worse)} did worse than an ordinary bowler would have in {"his" if len(worse) == 1 else "their"} shoes over this stretch.'
    else:
        s += ' Every bowler shown did better than an ordinary bowler would have in their shoes.'
    return s


# ---- prose that depends on the direction of a result ----------------------------------------------
SOURCE_NAMES = {'bowler_effect': 'the bowler', 'dealt': 'the conditions they were given', 'shaped': 'match situations',
                'baseline (pace or spin)': 'being a spinner or a fast bowler'}
top = max(SOURCE_NAMES, key=share)
sources_title = ('Once luck is set aside, the bowler matters most' if top == 'bowler_effect'
                 else f'Once luck is set aside, {SOURCE_NAMES[top]} matter most')
dealt_small = display_share('dealt') < 0.02
if dealt_small:
    dealt_txt = ('The conditions they were given add almost nothing to the gaps between bowlers: over 100 wickets the good '
                 'and bad draws mostly even out' +
                 (', and the bowlers who were dealt harder conditions tended to be the better ones, so conditions '
                  'narrowed the gaps rather than widened them.' if share('dealt') < 0 else '.'))
else:
    dealt_txt = f"The conditions they were given account for {display_pct('dealt')}."
sources_rest = f"The bowler's own ability accounts for {display_pct('bowler_effect')} of the real differences. {dealt_txt}"
sources_detail = (f"The bowler accounts for {display_pct('bowler_effect')} of the real differences, being a spinner or a "
                  f"fast bowler for {display_pct('baseline (pace or spin)')}, match situations for {display_pct('shaped')} "
                  f"and the conditions they were given for {display_pct('dealt')}. {dealt_txt if dealt_small else ''}").strip()
sources_meaning = ("Conditions still move an average ball by ball (next finding), so check them before judging one bowler's "
                   "record. But across bowlers who reach 100 wickets, the bowler is the main story."
                   if dealt_small else
                   "Before praising or blaming a bowler's average, ask where they played and who they bowled at.")

lyon = bowler('NM Lyon')
lyon_gap = lyon['xAvg'] - lyon['baseline']
GROUPS = M['dealt'] + M['shaped']
lyon_top = max(GROUPS, key=lambda g: abs(lyon[g]))
if abs(lyon_gap) < 1:
    lyon_conditions = f'About typical for a spinner ({lyon["baseline"]:.1f}).'
else:
    lyon_conditions = (f'{"Harder" if lyon_gap > 0 else "Easier"} than typical for a spinner ({lyon["baseline"]:.1f}); '
                       f'the biggest single factor was {lyon_top.lower()} ({num(lyon[lyon_top], 1)}).')
lyon_effect_words = (f'he did {"better" if lyon["bowler_effect"] < 0 else "worse"} than an ordinary spinner would have '
                     f'in the same spots.')

# The bowler whose conditions lowered his expected average the most below typical for his type
helped = min(D['bowlers'], key=lambda b: b['xAvg'] - b['baseline'])
GROUP_WORDS = {'Opposition line-up': 'the batting line-ups he faced', 'Venue & home': 'where he bowled',
               'Era & umpires': 'the era and umpires', 'Match phase': 'the innings and day he bowled in',
               'Bowling partner': 'his bowling partners', 'Bowling arm': 'his bowling arm',
               "Who's at the crease": 'the batters he bowled at', 'Batter set or new': 'how often batters were new',
               'Match state': 'the state of the match', 'Role & usage': 'when and how he was used'}
helped_groups = [g for g in sorted(GROUPS, key=lambda g: helped[g]) if helped[g] < 0][:2]
helped_gap = helped['baseline'] - helped['xAvg']
helped_type = 'spinner' if helped['bowler_type'] == 'spin' else 'fast bowler'
helped_sentence = (
    f"Some low averages owe a lot to the conditions. {display_name(helped)} averaged {helped['actual']:.1f} over his first "
    f"{M['window']} wickets, well below the {helped['baseline']:.1f} a {helped_type} averages in typical conditions. "
    f"But his conditions were easy, mostly because of {' and '.join(GROUP_WORDS[g] for g in helped_groups)}, so an ordinary "
    f"{helped_type} bowling the same balls would have averaged {helped['xAvg']:.1f}. His conditions were worth about "
    f"{helped_gap:.1f} runs per wicket, and he did {abs(helped['bowler_effect']):.1f} runs per wicket "
    f"{'worse' if helped['bowler_effect'] > 0 else 'better'} than an ordinary {helped_type} would have in them.")

hand = effect('bat_hand_x_type', 'opposite', 'spin')
hand_sentence = (f"spinners do about {abs(hand['avg_pct']):.0f}% {'better' if hand['avg_pct'] < 0 else 'worse'} when the batter's hand is "
                 f'opposite their bowling arm (a right-arm spinner to a left-hander, or a left-arm spinner to a right-hander).'
                 if clear(hand) else "for spinners, whether the batter is left- or right-handed makes no clear difference.")
hand_sentence = hand_sentence[0].upper() + hand_sentence[1:]
inn4 = effect('innings_x_type', '4', 'spin')
inn4_sentence = (f"A spinner who would average {BASE:.0f} in typical conditions averages about {BASE * (1 + inn4['avg_pct'] / 100):.0f} "
                 f"in the fourth innings" + (', when the pitch is at its most worn.' if inn4['avg_pct'] < 0 else '.'))
patterns = [("Batter's hand", hand_sentence)] + ([('Fourth innings', inn4_sentence)] if clear(inn4) else [])

lineup_runs = runs(effect('lineup', '[46.0, inf)', 'pace')['avg_pct'] - effect('lineup', '[28.0, 31.0)', 'pace')['avg_pct'])
home_runs = runs(sum(effect('home_x_type', 'away', t)['avg_pct'] - effect('home_x_type', 'home', t)['avg_pct'] for t in ('pace', 'spin')) / 2)
partner_runs = runs(effect('partner', '[38.0, inf)', 'pace')['avg_pct'] - effect('partner', '[0.0, 26.0)', 'pace')['avg_pct'])
partner_sentence = (f'A strong rather than a weak bowler at the other end is worth about {partner_runs:.1f}.'
                    if any(clear(e) for e in D['effects'] if e['variable'] == 'partner') else
                    "Who bowls at the other end doesn't measurably change a bowler's average.")

def spread(var, t):
    """Share-weighted sd of a variable's level effects for one bowler type: how much it typically moves an average."""
    rows = [e for e in D['effects'] if e['variable'] == var and e['bowler_type'] == t]
    tot = sum(e['share'] for e in rows)
    mean = sum(e['share'] * e['avg_pct'] for e in rows) / tot
    return (sum(e['share'] * (e['avg_pct'] - mean) ** 2 for e in rows) / tot) ** 0.5

TYPE_WORD = {'pace': 'fast bowlers', 'spin': 'spinners'}
country_first = [t for t in ('pace', 'spin') if spread('country_x_type', t) > spread('lineup', t)]
if not country_first:
    cond_lead = "The opposition's batting is the biggest condition."
    cond_rest = f'Facing a weak line-up instead of a strong one can move an average by about {lineup_runs:.0f} runs per wicket.'
else:
    cond_lead = 'Who they bowl at and where matter most.'
    cond_rest = (f'Facing a weak line-up instead of a strong one can move an average by about {lineup_runs:.0f} runs per wicket; '
                 f'for {" and ".join(TYPE_WORD[t] for t in country_first)}, the country they bowl in matters even more.')

def arm_words(t):
    gap = effect('type', 'left', t)['avg_pct'] - effect('type', 'right', t)['avg_pct']
    if not (clear(effect('type', 'left', t)) or clear(effect('type', 'right', t))):
        return f"left- and right-arm {TYPE_WORD[t]} average about the same"
    return f"left-arm {TYPE_WORD[t]} average about {abs(gap):.0f}% {'less' if gap < 0 else 'more'} than right-arm ones"
arm_sentence = f"{arm_words('pace').capitalize()}, and {arm_words('spin')}."
patterns.append(('Bowling arm', arm_sentence))
patterns_list = ''.join(f'<li><strong>{name}.</strong> {text}</li>' for name, text in patterns)

SITU = {'wkt vs new batter (<10 balls)': 'against new batters', 'wkt vs new ball (<15 overs)': 'with the new ball',
        'wkt vs top order (1-4)': 'against the top order', 'wkt vs late in spell (over 6+)': 'late in a spell',
        'wkt vs at home': 'at home', 'wkt vs after 3+ dots': 'after three dot balls in a row'}
or_list = lambda a: a[0] if len(a) == 1 else ', '.join(a[:-1]) + ' or ' + a[-1]
flat = [w for c, w in SITU.items() if split(c) < 0.15]
some = [w for c, w in SITU.items() if split(c) >= 0.15]
situ_sentence = (f'Being unusually good at taking wickets {or_list(flat)} did not carry over from one half to the next.' if flat else '')
if some:
    and_list = some[0] if len(some) == 1 else ', '.join(some[:-1]) + ' and ' + some[-1]
    situ_sentence += f' Only wicket-taking {and_list} carried over at all, and much less than keeping runs down.'

missing_sentence = (f"{M['n_missing_tests']} of the {M['n_tests_since_cutoff']} Tests since 2007 aren't in the public data (mostly "
                    "Afghanistan's), so a few bowlers have some wickets skipped." if M['n_missing_tests']
                    else 'Every Test since 2007 is in the data.')

values = {
    'window': M['window'], 'half': M['window'] // 2,
    'n_tests': M['n_tests'], 'n_bowlers': M['n_bowlers'],
    'n_balls': f"{M['n_deliveries_model'] / 1e6:.1f} million",
    'n_bowlers_model': M['n_bowlers_model'],
    'first_year': M['date_range'][0][:4], 'end_year': M['data_end_year'],
    'luck': pct(1 - signal()),
    'rel_raw': num(M['raw_half_reliability'][0]),
    'sources_title': sources_title, 'sources_lead': sources_title + '.', 'sources_rest': sources_rest,
    'sources_detail': sources_detail, 'sources_meaning': sources_meaning,
    'pace_base': f"{M['baseline_by_type']['pace']:.1f}", 'spin_base': f"{M['baseline_by_type']['spin']:.1f}",
    'run_rel': num(split('run-control skill')), 'wkt_rel': num(split('wicket-taking skill')),
    'noball_rel': num(split('wides+no-balls per 100')),
    'lyon_actual': f"{lyon['actual']:.1f}", 'lyon_expected': f"{lyon['xAvg']:.1f}",
    'lyon_effect': num(lyon['bowler_effect'], 1), 'lyon_conditions': lyon_conditions, 'lyon_effect_words': lyon_effect_words,
    'helped_sentence': helped_sentence,
    'home_runs': f'{home_runs:.1f}', 'partner_sentence': partner_sentence, 'sources_sub': sources_sub,
    'patterns_list': patterns_list,
    'cond_lead': cond_lead, 'cond_rest': cond_rest, 'situ_sentence': situ_sentence,
    'bowlers_sentence': bowlers_sentence(), 'missing_sentence': missing_sentence,
    'luck_chart': luck_bar(f'First {M["window"]} wickets'),
    'sources_chart': sources_bar(f'First {M["window"]} wickets'),
    'conditions_chart': condition_rows(),
    'carry_chart': carry_rows(),
    'bowlers_chart': bowler_rows(),
}

page = open(os.path.join(HERE, 'src', 'plain_template.html')).read()
for k, v in values.items():
    page = page.replace('{{' + k + '}}', str(v))
assert '{{' not in page, page[page.index('{{'):page.index('{{') + 40]

os.makedirs(os.path.join(HERE, 'publish'), exist_ok=True)
with open(os.path.join(HERE, 'publish', 'Behind the Bowling Average.html'), 'w') as f:      # publish copy
    f.write(page)
standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + page.replace('<header', '</head>\n<body>\n<header', 1) + '\n</body>\n</html>\n')
with open(os.path.join(HERE, 'Behind the Bowling Average.html'), 'w') as f:
    f.write(standalone)
print('written', len(standalone) // 1024, 'KB')
