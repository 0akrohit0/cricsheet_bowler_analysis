# ---- Pre-debut record in white-ball internationals (ODI and T20I only; no domestic cricket) ----
WB_CACHE = CACHE_DIR / 'white_ball_bowling.pkl'
study_ids = set(bowlers.index)

def parse_white_ball(json_dir, keep_ids):
    rows = []
    for file_path in sorted(json_dir.glob('*.json')):
        with open(file_path, 'r') as f:
            m = json.load(f)
        info = m.get('info', {})
        if info.get('team_type') != 'international' or info.get('match_type') not in ('ODI', 'T20', 'IT20'):
            continue
        reg = info.get('registry', {}).get('people', {})
        date = info.get('dates', [None])[0]
        for inn in m.get('innings', []):
            for over in inn.get('overs', []):
                for d in over.get('deliveries', []):
                    bid = reg.get(d.get('bowler'))
                    if bid not in keep_ids: continue
                    ex, r = d.get('extras', {}), d.get('runs', {})
                    rows.append((bid, date, info['match_type'], int(file_path.stem),
                                 int('wides' not in ex and 'noballs' not in ex),
                                 r.get('total', 0) - ex.get('byes', 0) - ex.get('legbyes', 0) - ex.get('penalty', 0),
                                 int(any(w.get('kind') in BOWLER_WICKET_KINDS for w in d.get('wickets', [])))))
    out = pd.DataFrame(rows, columns=['bowler_id', 'date', 'format', 'match_id', 'legal', 'runs', 'wkt'])
    out['date'] = pd.to_datetime(out['date'])
    return out

wb = pd.read_pickle(WB_CACHE) if WB_CACHE.exists() else None
if wb is None or not study_ids <= set(wb.attrs.get('bowler_ids', [])):
    wb = parse_white_ball(JSON_DIR, study_ids)
    wb.attrs['bowler_ids'] = sorted(study_ids)
    wb.to_pickle(WB_CACHE)

wb = wb[wb['date'] < wb['bowler_id'].map(bowlers['first_test'])]
wb['fmt'] = np.where(wb['format'] == 'ODI', 'ODI', 'T20I')
pre = wb.groupby(['bowler_id', 'fmt']).agg(matches=('match_id', 'nunique'), legal=('legal', 'sum'),
                                           runs=('runs', 'sum'), wkts=('wkt', 'sum')).unstack('fmt')
profile = pd.DataFrame(index=bowlers.index)
profile['is_spinner'] = (bowlers['bowler_type'] == 'spin').astype(int)
profile['is_left_arm'] = (bowlers['bowler_arm'] == 'left').astype(int)
profile['age_at_debut'] = bowlers['age_at_debut'].fillna(bowlers['age_at_debut'].median())
profile['debut_year'] = bowlers['first_test'].dt.year
profile['pre-debut ODIs'] = pre.get(('matches', 'ODI'), pd.Series(dtype=float)).reindex(bowlers.index).fillna(0)
profile['pre-debut T20Is'] = pre.get(('matches', 'T20I'), pd.Series(dtype=float)).reindex(bowlers.index).fillna(0)
# ODI economy and strike rate, shrunk toward the study bowlers' pooled ODI rates (300 balls, 6 wickets)
odi = pre.xs('ODI', axis=1, level='fmt').reindex(bowlers.index).fillna(0) if 'ODI' in pre.columns.get_level_values('fmt') else None
pool_econ = 6 * odi['runs'].sum() / odi['legal'].sum()
pool_sr = odi['legal'].sum() / odi['wkts'].sum()
profile['pre-debut ODI economy'] = (6 * odi['runs'] + pool_econ * 300) / (odi['legal'] + 300)
profile['pre-debut ODI strike rate'] = (odi['legal'] + pool_sr * 6) / (odi['wkts'] + 6)
print(f"{(profile['pre-debut ODIs'] > 0).sum()} of {len(profile)} bowlers played ODIs before their Test debut; "
      f"{(profile['pre-debut T20Is'] > 0).sum()} played T20Is")

# ---- Which first-half measures and attributes predict the second half? -------------------------
# Target: second-half average (log), and second-half skill (log xAvg/avg). Predictors are all fixed
# before wicket 26, except the context the bowler is dealt in the second half, which is outside their control.
y_avg2 = np.log(h2['average'])
y_skill2 = h2['overall skill']
FEATURE_SETS = {
    'first-half average only':             pd.DataFrame({'log avg h1': np.log(h1['average'])}),
    'profile (type, arm, age, era, white-ball record)': profile,
    'context dealt in the second half':    ctx_h2[DEALT + ['baseline']],
    'first-half skill components':         h1[COMPONENTS],
}
FEATURE_SETS['profile + 2nd-half context'] = pd.concat([profile, ctx_h2[DEALT + ['baseline']]], axis=1)
FEATURE_SETS['profile + 2nd-half context + 1st-half run control'] = pd.concat(
    [profile, ctx_h2[DEALT + ['baseline']], h1[['run-control skill']]], axis=1)
FEATURE_SETS['everything'] = pd.concat([profile, ctx_h2[DEALT + ['baseline']], h1[COMPONENTS]], axis=1)

def loo_r2(X, y):
    X = X.loc[y.index].to_numpy(float)
    model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 40)))
    pred = cross_val_predict(model, X, y.to_numpy(), cv=KFold(len(y)))
    return r2_score(y, pred)

pred_table = pd.DataFrame({
    'LOO R² for 2nd-half average': {k: loo_r2(X, y_avg2) for k, X in FEATURE_SETS.items()},
    'LOO R² for 2nd-half skill': {k: loo_r2(X, y_skill2) for k, X in FEATURE_SETS.items()},
})
pred_table.round(3)

# The ceiling: even a perfect predictor can't explain the sampling noise in a half-window average.
# Resample each bowler's second-half Tests to estimate that noise.
h2w = wd[wd['half'] == 2]
pm = h2w.groupby(['bowler_id', 'match_id']).agg(runs=('bowler_runs', 'sum'), wkts=('is_wicket', 'sum')).reset_index()
pm_codes, pm_order = pd.factorize(pm['bowler_id'])
pm_rows = [np.flatnonzero(pm_codes == i) for i in range(len(pm_order))]
boot_log_avg2 = []
for _ in range(500):
    take = np.concatenate([RNG.choice(r, size=len(r), replace=True) for r in pm_rows])
    runs = np.bincount(pm_codes[take], pm['runs'].to_numpy()[take], minlength=len(pm_order))
    wkts = np.bincount(pm_codes[take], pm['wkts'].to_numpy()[take], minlength=len(pm_order))
    boot_log_avg2.append(np.log(runs / np.maximum(wkts, 1)))
noise_var2 = np.array(boot_log_avg2).var(0).mean()
R2_CEILING = 1 - noise_var2 / y_avg2.var()
print(f'Ceiling: at most {R2_CEILING:.2f} of the variance in second-half (log) averages is predictable at all')

# Pre-debut white-ball record vs Test skill over the whole window
wb_vs_test = pd.DataFrame({
    f'{a} vs {b}': boot_spearman(profile.loc[full.index, a], full[b])
    for a in ['pre-debut ODI economy', 'pre-debut ODI strike rate']
    for b in ['run-control skill', 'wicket-taking skill', 'overall skill']
}, index=['rho', 'lo', 'hi']).T
has_odi = profile['pre-debut ODIs'] >= 10
print(f'Bowlers with 10+ pre-debut ODIs: {has_odi.sum()}')
wb_vs_test_10 = pd.DataFrame({
    f'{a} vs {b}': boot_spearman(profile.loc[has_odi, a], full.loc[profile.index[has_odi], b])
    for a in ['pre-debut ODI economy', 'pre-debut ODI strike rate']
    for b in ['run-control skill', 'wicket-taking skill', 'overall skill']
}, index=['rho', 'lo', 'hi']).T
pd.concat({f'all {len(profile)} (shrunk)': wb_vs_test, '10+ ODIs': wb_vs_test_10}, axis=1).round(2)
