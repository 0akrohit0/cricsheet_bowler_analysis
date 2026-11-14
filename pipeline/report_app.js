const D = DATA, M = D.meta;
const pct = (v, d = 0) => (100 * v).toFixed(d) + '%';
// A share-of-real-variance estimate below zero means the noise accounts for all of the observed spread
const realPct = (v) => (v < 0 ? '≈0%' : pct(v));
const signedPct = (v, d = 0) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) + '%';
const byKey = (arr, k) => Object.fromEntries(arr.map((r) => [r[k], r]));
const shares = byKey(D.variance_shares, 'part');
const signal = byKey(D.signal, 'quantity');
const split = byKey(D.split_half, 'component');
const sens = byKey(D.sensitivity, 'measure');
const sensCols = Object.keys(D.sensitivity[0]).filter((k) => k !== 'measure');
const effect = (v, level, t) => D.effects.find((e) => e.variable === v && e.level === level && e.bowler_type === t);
const SHARE = (k) => shares[k]['share of real variance'];

// ---- numbers in the prose -----------------------------------------------------------------
const homeGap = (effect('home_x_type', 'away', 'pace').avg_pct - effect('home_x_type', 'home', 'pace').avg_pct +
  effect('home_x_type', 'away', 'spin').avg_pct - effect('home_x_type', 'home', 'spin').avg_pct) / 2;
const partnerLevels = D.effects.filter((e) => e.variable === 'partner' && e.bowler_type === 'pace');
const partnerGap = Math.max(...partnerLevels.map((e) => e.avg_pct)) - Math.min(...partnerLevels.map((e) => e.avg_pct));
const pred = byKey(D.prediction, 'features');
const fit = byKey(D.model_fit, 'model');
const BIND = {
  window: M.window, n_bowlers: M.n_bowlers, sens_window: M.sensitivity_window,
  date_range: `${M.date_range[0].slice(0, 4)}–${M.date_range[1].slice(0, 4)}`,
  n_deliveries: (M.n_deliveries_model / 1e6).toFixed(2) + 'M', n_bowlers_model: M.n_bowlers_model,
  noise_pct: pct(1 - signal['actual average']['share of variance that is real']),
  raw_rel: fmtPlain(M.raw_half_reliability[0], 2),
  share_dealt: pct(SHARE('dealt')), share_shaped: pct(SHARE('shaped')), share_bowler: pct(SHARE('bowler_effect')),
  share_base: pct(SHARE('baseline (pace or spin)')),
  rel_run: fmtPlain(split['run-control skill'].reliability, 2), rel_wkt: fmtPlain(split['wicket-taking skill'].reliability, 2),
  lineup_weak: signedPct(effect('lineup', '[28.0, 31.0)', 'pace').avg_pct),
  lineup_strong: signedPct(effect('lineup', '[46.0, inf)', 'pace').avg_pct),
  home_gap: Math.round(homeGap) + '%', partner_gap: Math.round(partnerGap) + '%',
  spin_india: signedPct(effect('country_x_type', 'India', 'spin').avg_pct),
  spin_aus: signedPct(effect('country_x_type', 'Australia', 'spin').avg_pct),
  sd_obs: signal['actual average']['observed sd'].toFixed(1), sd_true: signal['actual average']['true sd (noise removed)'].toFixed(1),
  sens_n: sens.n_bowlers[sensCols[3]], sens_bowler: pct(sens['real share: bowler_effect'][sensCols[3]]),
  rel_extras: split['wides+no-balls per 100'].reliability.toFixed(2), rel_bowled: split['% bowled or lbw'].reliability.toFixed(2),
  rel_keeper: split['% caught by keeper'].reliability.toFixed(2),
  r2_profile: pred['profile (type, arm, age, era, white-ball record)']['LOO R² for 2nd-half average'].toFixed(2),
  r2_ceiling: D.r2_ceiling.toFixed(2), n_odi: M.n_pre_debut_odi,
  ll_glm: fit['additive GLM (used)']['wicket log-loss'].toFixed(4), ll_gbm: fit['gradient boosting']['wicket log-loss'].toFixed(4),
};
const N = M.window, H = N / 2, noise = 1 - signal['actual average']['share of variance that is real'];
Object.assign(BIND, {
  half_a: `1–${H}`, half_b: `${H + 1}–${N}`, half_n: H,
  h_luck: noise > 0.5 ? `Over ${N} wickets, most of the difference between bowlers is luck.`
    : `Over ${N} wickets, about ${pct(noise)} of the difference between bowlers is luck.`,
  raw_phrase: M.raw_half_reliability[0] < 0.3 ? 'barely predicts' : 'only partly predicts',
  h_sources: SHARE('bowler_effect') > SHARE('dealt')
    ? 'Of the real spread, the bowler matters more than the conditions they were given.'
    : 'Of the real spread, the conditions a bowler was given matter more than the bowler.',
  wkt_phrase: split['wicket-taking skill'].reliability < 0.1 ? "doesn't repeat at all" : 'barely repeats',
});
(function () {
  const r = split['run-control skill'];
  BIND.run_pred_phrase = r.pred_lo > 0 && r.q < 0.1
    ? `and predicts how far the bowler beats the conditions later (ρ = ${r['predicts 2nd-half skill'].toFixed(2)})`
    : `and points the same way for later performance (ρ = ${r['predicts 2nd-half skill'].toFixed(2)}), though with ${M.n_bowlers} bowlers that interval includes zero`;
  const nice = (p) => p.replace('pre-debut ODI ', 'ODI ').replace(' vs ', ' with Test ').replace(' skill', '');
  const sig = D.white_ball.filter((w) => w.all_lo > 0 || w.all_hi < 0).map((w) => nice(w.pair));
  BIND.odi_phrase = sig.length
    ? `Of the pre-debut ODI measures, only ${sig.length > 1 ? sig.slice(0, -1).join(', ') + ' and ' + sig.at(-1) : sig[0]} show a clear link (see the check below).`
    : 'Pre-debut ODI records show no clear link with Test skill.';
})();
(function () {
  const blank = sensCols.filter((c) => sens['real share: dealt'][c] === null);
  BIND.sens_blank_note = blank.length
    ? `Shares are left blank for ${blank.join(' and ')} (${blank.map((c) => sens.n_bowlers[c]).join(', ')} bowlers): so little of the spread is real there (${blank.map((c) => realPct(sens['share real'][c])).join(', ')}) that the shares can't be estimated.`
    : '';
})();
document.querySelectorAll('[data-v]').forEach((n) => { n.textContent = BIND[n.dataset.v] ?? '—'; });

// ---- noise vs real stack ------------------------------------------------------------------
(function () {
  const real = signal['actual average']['share of variance that is real'];
  const parts = [['baseline (pace or spin)', '--base', 'Pace/spin'], ['dealt', '--dealt', 'Dealt'],
    ['shaped', '--shaped', 'Shaped'], ['bowler_effect', '--bowler', 'Bowler']];
  const box = document.getElementById('stack-noise');
  const noise = document.createElement('div');
  noise.className = 'noise'; noise.style.flex = String(1 - real); noise.textContent = 'Noise ' + pct(1 - real);
  noise.title = `Sampling noise: ${pct(1 - real)} of the variance`;
  box.appendChild(noise);
  for (const [k, c, lab] of parts) {
    const s = Math.max(0, SHARE(k)) * real, d = document.createElement('div');
    d.style.flex = String(s); d.style.background = `var(${c})`;
    d.textContent = s > 0.07 ? `${lab} ${pct(s)}` : '';
    d.title = `${lab}: ${pct(s)} of all variance (${pct(SHARE(k))} of the real part)`;
    box.appendChild(d);
  }
})();

// ---- share of real spread by source --------------------------------------------------------
const NICE = { 'baseline (pace or spin)': 'Pace or spin', bowler_effect: 'The bowler (beyond conditions)' };
function drawShares() {
  const rows = [];
  rows.push({ label: NICE['baseline (pace or spin)'], value: 100 * SHARE('baseline (pace or spin)'), color: css('--base') });
  const sorted = (gs) => gs.slice().sort((a, b) => SHARE(b) - SHARE(a));
  for (const g of sorted(M.dealt)) rows.push({ label: g, value: 100 * SHARE(g), color: css('--dealt'), note: 'Dealt: outside the bowler\'s control' });
  for (const g of sorted(M.shaped)) rows.push({ label: g, value: 100 * SHARE(g), color: css('--shaped'), note: 'Shaped: partly the bowler\'s or team\'s own doing' });
  rows.push({ label: NICE.bowler_effect, value: 100 * SHARE('bowler_effect'), color: css('--bowler') });
  hbars(document.getElementById('chart-shares'), rows, { unit: '%', decimals: 0, labelW: 220, rowH: 28 });
}

// ---- conditions, one by one -----------------------------------------------------------------
const binLabel = (s) => {
  const m = s.match(/^\[(-?[\d.]+|-inf), (-?[\d.]+|inf)\)$/);
  if (!m) return s;
  const a = m[1] === '-inf' ? null : +m[1], b = m[2] === 'inf' ? null : +m[2];
  const f = (x) => (Number.isInteger(x) ? x : x.toFixed(1)).toString().replace('-', '−');
  if (a === null || a === 0) return `under ${f(b)}`;
  if (b === null) return `${f(a)}+`;
  return `${f(a)}–${f(b)}`;
};
const binStart = (s) => { const m = s.match(/^\[(-?[\d.]+|-inf)/); return m ? (m[1] === '-inf' ? -1e9 : +m[1]) : 0; };
const EFFECTS = [
  { v: 'lineup', name: 'Opposition line-up', title: "Opposition line-up: the batting side's best seven", sub: 'Mean pre-match Test average of their top seven batters.', both: false, order: 'bin' },
  { v: 'home_x_type', name: 'Home or away', title: 'Home, away or neutral venue', sub: 'Host country from the series name; UAE treated as neutral.', both: true, order: ['home', 'away', 'neutral'] },
  { v: 'country_x_type', name: 'Host country', title: 'Host country', sub: 'Where pace and spin are cheap or dear, on top of home advantage.', both: true, order: 'value' },
  { v: 'partner', name: 'Bowling partner', title: 'Bowler at the other end', sub: "The partner's pre-match Test average.", both: false, order: 'bin' },
  { v: 'innings_x_type', name: 'Innings', title: 'Which innings of the match', sub: 'With the lead, wickets down and overs into the match held at typical values.', both: true, order: ['1', '2', '3', '4'], fmt: (l) => ['', '1st', '2nd', '3rd', '4th'][+l] + ' innings' },
  { v: 'day_x_type', name: 'Days into match', title: 'Overs into the match (≈ 90 per day)', sub: 'Holding the innings fixed.', both: true, order: 'bin', fmt: (l) => 'overs ' + binLabel(l) },
  { v: 'bat_hand_x_type', name: 'Hand matchup', title: "Batter's hand against the bowler's arm", sub: "Same side: right-arm to right-hander, left to left. Opposite side: e.g. an off-spinner to a left-hander.", both: true, order: ['same', 'opposite', 'unknown'], fmt: (l) => l + ' side', shaped: true },
  { v: 'type', name: 'Bowling arm', title: 'Bowling arm, within type', sub: 'Pace and spin each compared with their own typical mix of arms.', both: true, order: ['right', 'left'], fmt: (l) => l + '-arm' },
  { v: 'drs', name: 'DRS', title: 'DRS reviews recorded in the match', both: false, order: ['0', '1'], fmt: (l) => (l === '1' ? 'with DRS' : 'no DRS') },
  { v: 'era', name: 'Era', title: 'Era', both: false, order: 'bin', fmt: (l) => l.replace(/^\[(\d+), (\d+)\)$/, (_, a, b) => `${a}–${Math.min(+b - 1, 2026)}`) },
  { v: 'umpire_lbw', name: 'Umpires', title: "Umpires' LBW rate in other matches", sub: 'Index: 1.00 = league rate.', both: false, order: 'bin' },
  { v: 'toss_field', name: 'Toss', title: 'Bowling side won the toss and chose to field', both: false, order: ['0', '1'], fmt: (l) => (l === '1' ? 'chose to field' : 'otherwise') },
  { v: 'set', name: 'Batter set? (shaped)', title: 'Balls the batter has faced so far (shaped)', sub: 'Partly the bowler\'s doing: bowl well and more of your balls go to new batters.', both: true, order: 'bin', shaped: true },
  { v: 'workload', name: 'Overs bowled (shaped)', title: 'Overs the bowler has already bowled in the match (shaped)', sub: 'Runs backwards: captains keep bowling whoever is succeeding.', both: true, order: 'bin', shaped: true },
  { v: 'ball_age_x_type', name: 'Ball age (shaped)', title: 'Overs since the new ball (shaped)', sub: 'Partly a captain\'s choice: spinners bowled early with a new ball are bowled when it is already turning.', both: true, order: 'bin', shaped: true },
];
let currentEffect = EFFECTS[0];
function drawEffect() {
  const cfg = currentEffect;
  let levels = [...new Set(D.effects.filter((e) => e.variable === cfg.v).map((e) => e.level))];
  if (Array.isArray(cfg.order)) levels = cfg.order.filter((l) => levels.includes(l));
  else if (cfg.order === 'bin') levels.sort((a, b) => binStart(a) - binStart(b));
  else levels.sort((a, b) => (effect(cfg.v, a, 'pace')?.avg_pct ?? 0) - (effect(cfg.v, b, 'pace')?.avg_pct ?? 0));
  const types = cfg.both ? ['pace', 'spin'] : ['pace'];
  const rows = [];
  for (const l of levels) for (const t of types) {
    const e = effect(cfg.v, l, t); if (!e) continue;
    const name = (cfg.fmt ? cfg.fmt(l) : binLabel(l));
    rows.push({ label: cfg.both ? `${name} · ${t}` : name, value: e.avg_pct, lo: e.avg_lo, hi: e.avg_hi,
      color: cfg.both ? css(t === 'pace' ? '--pace' : '--spin') : css('--accent'),
      note: `Strike-rate part ${signedPct(e.sr_pct, 1)}, economy part ${signedPct(e.econ_pct, 1)}; ${pct(e.share, 1)} of ${t} deliveries` });
  }
  document.getElementById('effect-title').textContent = cfg.title;
  document.getElementById('effect-sub').textContent = (cfg.sub || '') + (cfg.both ? '' : ' Same effect for pace and spin in the model.');
  document.querySelector('#conditions .legend').hidden = !cfg.both;
  hbars(document.getElementById('chart-effects'), rows, { unit: '%', decimals: 1, labelW: 200, rowH: 28 });
}
(function () {
  const box = document.getElementById('effect-chips');
  EFFECTS.forEach((cfg, i) => {
    const b = document.createElement('button');
    b.className = 'chip'; b.textContent = cfg.name; b.setAttribute('aria-pressed', i === 0 ? 'true' : 'false');
    b.addEventListener('click', () => {
      box.querySelectorAll('.chip').forEach((c) => c.setAttribute('aria-pressed', 'false'));
      b.setAttribute('aria-pressed', 'true'); currentEffect = cfg; drawEffect();
    });
    box.appendChild(b);
  });
})();

// ---- skill: reliability and prediction ---------------------------------------------------------
const SKILL_NAMES = {
  'overall skill': 'Overall (beats the conditions)', 'run-control skill': 'Run control', 'wicket-taking skill': 'Wicket-taking',
  'wkt vs new batter (<10 balls)': 'Wickets vs new batters', 'wkt vs set batter (30+ balls)': 'Wickets vs set batters',
  'wkt vs top order (1-4)': 'Wickets vs top order', 'wkt vs tail (8-11)': 'Wickets vs tail',
  'wkt vs new ball (<15 overs)': 'Wickets with the new ball', 'wkt vs old ball (40+ overs)': 'Wickets with the old ball',
  'wkt vs early in spell (overs 1-3)': 'Wickets early in a spell', 'wkt vs late in spell (over 6+)': 'Wickets late in a spell',
  'wkt vs after 3+ dots': 'Wickets after 3+ dot balls', 'wkt vs left-handers': 'Wickets vs left-handers',
  'wkt vs right-handers': 'Wickets vs right-handers', 'wkt vs at home': 'Wickets at home', 'wkt vs away': 'Wickets away',
  'new-vs-set gap': 'Gap: new vs set batters', 'top-vs-tail gap': 'Gap: top order vs tail',
  'new-vs-old-ball gap': 'Gap: new vs old ball', 'early-vs-late-spell gap': 'Gap: early vs late in spell',
  'home-vs-away gap': 'Gap: home vs away', '% bowled or lbw': '% wickets bowled or lbw',
  '% caught by keeper': '% caught by the keeper', 'wides+no-balls per 100': 'Wides + no-balls per 100 balls',
};
let skillKey = 'reliability';
function drawSkill() {
  const lo = skillKey === 'reliability' ? 'rel_lo' : 'pred_lo', hi = skillKey === 'reliability' ? 'rel_hi' : 'pred_hi';
  const rows = D.split_half.slice().sort((a, b) => b[skillKey] - a[skillKey]).map((r) => ({
    label: SKILL_NAMES[r.component] || r.component, value: r[skillKey], lo: r[lo], hi: r[hi],
    color: r[lo] > 0 || r[hi] < 0 ? css('--bowler') : css('--base'),
    note: skillKey === 'reliability' ? `Same trait, wickets ${BIND.half_a} vs ${BIND.half_b}` : `Trait in wickets ${BIND.half_a} vs beating the conditions in ${BIND.half_b} (q = ${r.q.toFixed(2)})`,
  }));
  document.getElementById('skill-title').textContent = skillKey === 'reliability'
    ? 'Reliability: does the trait show up in both halves?'
    : `Prediction: does the trait in wickets ${BIND.half_a} predict beating the conditions in wickets ${BIND.half_b}?`;
  hbars(document.getElementById('chart-skill'), rows, { decimals: 2, labelW: 230, rowH: 26, domain: [-0.5, 1] });
}
document.querySelectorAll('#skill-chips .chip').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#skill-chips .chip').forEach((c) => c.setAttribute('aria-pressed', 'false'));
  b.setAttribute('aria-pressed', 'true'); skillKey = b.dataset.k; drawSkill();
}));

// white-ball table
(function () {
  const t = document.getElementById('table-wb');
  const label = (p) => p.replace('pre-debut ODI ', 'ODI ').replace(' vs ', ' → Test ');
  const ci = (r, k) => `${r[k + '_rho'].toFixed(2)} <span style="color:var(--ink-3)">[${r[k + '_lo'].toFixed(2)}, ${r[k + '_hi'].toFixed(2)}]</span>`;
  t.innerHTML = `<thead><tr><th class="l">Pre-debut ODI record → Test skill</th><th>All ${M.n_bowlers} bowlers (shrunk)</th><th>${D.n_odi10} with 10+ ODIs</th></tr></thead><tbody>` +
    D.white_ball.map((r) => `<tr><td class="l">${label(r.pair)}</td><td class="n">${ci(r, 'all')}</td><td class="n">${ci(r, 'odi10')}</td></tr>`).join('') +
    `</tbody>`;
})();

// ---- bowler explorer ----------------------------------------------------------------------------
const bowlers = D.bowlers.slice().sort((a, b) => a.actual - b.actual);
const sel = document.getElementById('bowler-select');
bowlers.forEach((b) => { const o = document.createElement('option'); o.value = b.bowler_id; o.textContent = `${b.bowler} (${b.team}, ${b.bowler_type})`; sel.appendChild(o); });
const defaultBowler = bowlers.find((b) => b.bowler === 'NM Lyon') || bowlers[0];
sel.value = defaultBowler.bowler_id;
function drawBowler() {
  const b = D.bowlers.find((x) => x.bowler_id === sel.value);
  document.getElementById('bowler-figures').innerHTML =
    `${M.window} wkts <span>·</span> ${b.tests} Tests <span>·</span> avg ${b.actual.toFixed(2)} <span>·</span> SR ${b.strike_rate.toFixed(1)} <span>·</span> econ ${b.economy.toFixed(2)} <span>·</span> debut ${b.first_test.slice(0, 4)}`;
  document.getElementById('bowler-sub').textContent =
    `Conditions predicted ${b.xAvg.toFixed(1)}. The bowler effect is ${fmt(b.bowler_effect, 1)} runs per wicket (95% interval ${fmtPlain(b.bowler_effect_lo, 1)} to ${fmtPlain(b.bowler_effect_hi, 1)}).`;
  const steps = [...M.dealt, ...M.shaped].map((g) => ({ label: g, value: b[g], ci: [b[g + '_lo'], b[g + '_hi']] }));
  steps.push({ label: 'The bowler', value: b.bowler_effect, ci: [b.bowler_effect_lo, b.bowler_effect_hi] });
  waterfall(document.getElementById('chart-waterfall'), steps,
    { start: b.baseline, startLabel: `Typical ${b.bowler_type} conditions`, endLabel: 'Actual average' });
}
sel.addEventListener('change', drawBowler);

function drawScatter() {
  const all = D.bowlers.flatMap((b) => [b.actual, b.xAvg]);
  const lo = Math.floor(Math.min(...all) / 5) * 5, hi = Math.ceil(Math.max(...all) / 5) * 5;
  const best = D.bowlers.slice().sort((a, b) => a.bowler_effect - b.bowler_effect);
  const labels = [...best.slice(0, 3), ...best.slice(-2)].map((b) => b.bowler);
  scatter(document.getElementById('chart-scatter'), D.bowlers.map((b) => ({
    x: b.xAvg, y: b.actual, label: b.bowler, color: css(b.bowler_type === 'pace' ? '--pace' : '--spin'),
    tip: `<b>${b.bowler}</b> (${b.team})<br>Actual ${b.actual.toFixed(1)} · conditions predicted ${b.xAvg.toFixed(1)}<br>Bowler effect ${fmt(b.bowler_effect, 1)}`,
  })), { xlab: 'Average the conditions predict (xAvg)', ylab: `Actual average, first ${M.window} wickets`, domain: [lo, hi], labels });
}

// sortable table of all bowlers
const COLS = [
  { k: 'bowler', t: 'Bowler', l: true }, { k: 'team', t: 'Team', l: true }, { k: 'bowler_type', t: 'Type', l: true },
  { k: 'tests', t: 'Tests', d: 0 }, { k: 'actual', t: 'Average', d: 1 }, { k: 'xAvg', t: 'Predicted', d: 1 },
  { k: 'bowler_effect', t: 'Bowler effect', d: 1, signed: true, ci: true }, { k: 'dealt', t: 'Dealt', d: 1, signed: true },
  { k: 'shaped', t: 'Shaped', d: 1, signed: true },
  { k: 'run-control skill', t: 'Run control', d: 2, signed: true, good: 1 }, { k: 'wicket-taking skill', t: 'Wicket-taking', d: 2, signed: true, good: 1 },
];
let sortKey = 'actual', sortDir = 1;
function drawTable() {
  const rows = D.bowlers.slice().sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : a[sortKey] < b[sortKey] ? -1 : 0) * sortDir);
  const head = COLS.map((c) => `<th class="${c.l ? 'l' : ''}" aria-sort="${c.k === sortKey ? (sortDir > 0 ? 'ascending' : 'descending') : 'none'}"><button data-k="${c.k}">${c.t}${c.k === sortKey ? (sortDir > 0 ? ' ↑' : ' ↓') : ''}</button></th>`).join('');
  const cell = (r, c) => {
    const v = r[c.k];
    if (c.l) return `<td class="l">${v}</td>`;
    const txt = c.signed ? fmt(v, c.d) : v.toFixed(c.d);
    const cls = c.k === 'bowler_effect' ? (r.bowler_effect_hi < 0 ? 'good' : r.bowler_effect_lo > 0 ? 'bad' : '') : '';
    return `<td class="n ${cls}">${txt}${c.ci ? ` <span style="color:var(--ink-3)">[${fmtPlain(r.bowler_effect_lo, 1)}, ${fmtPlain(r.bowler_effect_hi, 1)}]</span>` : ''}</td>`;
  };
  document.getElementById('table-bowlers').innerHTML = `<thead><tr>${head}</tr></thead><tbody>${rows.map((r) => `<tr>${COLS.map((c) => cell(r, c)).join('')}</tr>`).join('')}</tbody>`;
  document.querySelectorAll('#table-bowlers th button').forEach((b) => b.addEventListener('click', () => {
    if (sortKey === b.dataset.k) sortDir *= -1; else { sortKey = b.dataset.k; sortDir = 1; }
    drawTable();
  }));
}

// ---- prediction and robustness ----------------------------------------------------------------
function drawPred() {
  const rows = D.prediction.map((r) => ({ label: r.features, value: r['LOO R² for 2nd-half average'], color: css('--accent') }));
  rows.push({ label: 'Ceiling (noise limit)', value: D.r2_ceiling, color: css('--base'), note: 'The most any predictor could explain' });
  hbars(document.getElementById('chart-pred'), rows, { decimals: 2, labelW: 320, rowH: 28, signed: false });
}
(function () {
  const show = ['n_bowlers', 'share real', 'real share: baseline (pace or spin)', 'real share: dealt', 'real share: shaped',
    'real share: bowler_effect', 'reliability: run-control skill', 'reliability: wicket-taking skill', 'predicts 2nd half: run-control skill',
    'predicts 2nd half: wicket-taking skill', 'reliability: raw average'];
  const nice = (m) => m.replace('real share: ', 'Share of real spread: ').replace('bowler_effect', 'the bowler').replace('baseline (pace or spin)', 'pace or spin')
    .replace('share real', 'Variance that is real').replace('n_bowlers', 'Bowlers').replace('reliability: ', 'Reliability, ')
    .replace('predicts 2nd half: ', 'Predicts 2nd half, ').replace('raw average', 'raw average');
  const t = document.getElementById('table-sens');
  t.innerHTML = `<thead><tr><th class="l">Measure</th>${sensCols.map((c) => `<th>${c}</th>`).join('')}</tr></thead><tbody>` +
    show.map((m) => `<tr><td class="l">${nice(m)}</td>${sensCols.map((c) => {
      const v = sens[m][c];
      if (v === null || v === undefined) return '<td class="n" style="color:var(--ink-3)">n/a</td>';
      return `<td class="n">${m === 'n_bowlers' ? v : m === 'share real' ? realPct(v) : m.startsWith('real share') ? pct(v) : fmtPlain(v, 2)}</td>`;
    }).join('')}</tr>`).join('') + '</tbody>';
})();

function drawAll() { drawShares(); drawEffect(); drawSkill(); drawBowler(); drawScatter(); drawPred(); }
drawAll(); drawTable();
let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(drawAll, 150); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', drawAll);
new MutationObserver(drawAll).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
