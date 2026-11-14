# ---- extra per-ball situation flags ----------------------------------------------------------
# Consecutive dot balls the batter has faced in this innings before this ball (scoreboard pressure)
is_dot = ((df['runs_total'] == 0) & (df['wides'] == 0)).astype(int)
faced = df['ball_faced'] == 1
run_id = (~is_dot.astype(bool)).groupby([df['match_id'], df['innings'], df['batter_id']]).cumsum()
streak = is_dot.groupby([df['match_id'], df['innings'], df['batter_id'], run_id]).cumsum()
df['dots_before'] = (streak - is_dot).where(faced, 0)   # dots in a row up to, not including, this ball

# Wicketkeepers: in each match, the fielding side's player who made a stumping in their career
# and took the most dismissals in that match
stumpers = set(df.loc[df['wicket_kind'] == 'stumped', 'fielder'].dropna())
fd = df[df['fielder'].isin(stumpers) & (df['fielder_sub'] == 0)]
keeper = (fd.groupby(['match_id', 'bowling_team', 'fielder']).size().reset_index(name='n')
          .sort_values('n', ascending=False).drop_duplicates(['match_id', 'bowling_team'])
          .set_index(['match_id', 'bowling_team'])['fielder'])
df['keeper'] = pd.MultiIndex.from_frame(df[['match_id', 'bowling_team']]).map(keeper)
df['caught_keeper'] = ((df['wicket_kind'] == 'caught') & (df['fielder'] == df['keeper']) & (df['is_wicket'] == 1)).astype(int)

wd = win.merge(ctx[['seq', 'p_wkt', 'mu_run']], on='seq').merge(
    df[['seq', 'dots_before', 'caught_keeper']], on='seq')
assert len(wd) == len(win)

# ---- bowler components, computed separately on each half of the window -----------------------
SITUATIONS = {
    'new batter (<10 balls)':  lambda d: d['batter_balls_before'] < 10,
    'set batter (30+ balls)':  lambda d: d['batter_balls_before'] >= 30,
    'top order (1-4)':         lambda d: d['batting_position'] <= 4,
    'tail (8-11)':             lambda d: d['batting_position'] >= 8,
    'new ball (<15 overs)':    lambda d: d['ball_age_overs'] < 15,
    'old ball (40+ overs)':    lambda d: d['ball_age_overs'] >= 40,
    'early in spell (overs 1-3)': lambda d: d['over_in_spell'] <= 3,
    'late in spell (over 6+)': lambda d: d['over_in_spell'] >= 6,
    'after 3+ dots':           lambda d: d['dots_before'] >= 3,
    'left-handers':            lambda d: d['batter_hand'] == 'left',
    'right-handers':           lambda d: d['batter_hand'] == 'right',
    'at home':                 lambda d: d['venue_for_bowler'] == 'home',
    'away':                    lambda d: d['venue_for_bowler'] == 'away',
}
K_W, K_R = 5, 150      # shrinkage: 5 pseudo-wickets and 150 pseudo-runs at the expected rate

def components(d):
    g = d.groupby('bowler_id')
    c = pd.DataFrame({
        'wkts': g['is_wicket'].sum(), 'x_wkts': g['p_wkt'].sum(),
        'runs': g['bowler_runs'].sum(), 'x_runs': g['mu_run'].sum(),
    })
    c['average'] = c['runs'] / c['wkts']
    c['xAvg'] = c['x_runs'] / c['x_wkts']
    # Every skill measure is oriented so that higher = better than the context predicts (log scale,
    # so 0.10 is about 10% better). Overall skill is exactly wicket-taking + run control.
    c['overall skill'] = np.log(c['xAvg'] / c['average'])
    c['wicket-taking skill'] = np.log((c['wkts'] + K_W) / (c['x_wkts'] + K_W))
    c['run-control skill'] = np.log((c['x_runs'] + K_R) / (c['runs'] + K_R))
    for name, f in SITUATIONS.items():
        s = d[f(d)].groupby('bowler_id')
        c[f'wkt vs {name}'] = np.log((s['is_wicket'].sum() + K_W) / (s['p_wkt'].sum() + K_W))
    c = c.fillna(0)
    # Contrasts: positive = relatively stronger in the first situation than the second
    c['new-vs-set gap'] = c['wkt vs new batter (<10 balls)'] - c['wkt vs set batter (30+ balls)']
    c['top-vs-tail gap'] = c['wkt vs top order (1-4)'] - c['wkt vs tail (8-11)']
    c['new-vs-old-ball gap'] = c['wkt vs new ball (<15 overs)'] - c['wkt vs old ball (40+ overs)']
    c['early-vs-late-spell gap'] = c['wkt vs early in spell (overs 1-3)'] - c['wkt vs late in spell (over 6+)']
    c['home-vs-away gap'] = c['wkt vs at home'] - c['wkt vs away']
    # Dismissal and discipline profile
    c['% bowled or lbw'] = 100 * d[d['wicket_kind'].isin(['bowled', 'lbw']) & (d['is_wicket'] == 1)].groupby('bowler_id').size().reindex(c.index, fill_value=0) / c['wkts']
    c['% caught by keeper'] = 100 * g['caught_keeper'].sum() / c['wkts']
    c['wides+no-balls per 100'] = 100 * (g['wides'].apply(lambda s: (s > 0).sum()) + g['noballs'].apply(lambda s: (s > 0).sum())) / g['is_legal'].sum()
    return c

h1, h2 = components(wd[wd['half'] == 1]), components(wd[wd['half'] == 2])
full = components(wd)
COMPONENTS = ['overall skill', 'wicket-taking skill', 'run-control skill'] + [f'wkt vs {n}' for n in SITUATIONS] + [
    'new-vs-set gap', 'top-vs-tail gap', 'new-vs-old-ball gap', 'early-vs-late-spell gap', 'home-vs-away gap',
    '% bowled or lbw', '% caught by keeper', 'wides+no-balls per 100']
print('Halves:', len(h1), 'bowlers; median balls per half',
      int(wd[wd.half == 1].groupby('bowler_id')['is_legal'].sum().median()), '/',
      int(wd[wd.half == 2].groupby('bowler_id')['is_legal'].sum().median()))
