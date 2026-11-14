first_test = df.groupby('bowler_id')['date'].min()
career_wkts = df.groupby('bowler_id')['is_wicket'].sum()

def build_windows(n_wickets):
    """Every delivery from a bowler's first Test up to and including the ball of their Nth wicket.

    Only bowlers whose first Test in the data is on or after FULL_COVERAGE_FROM are eligible, so that
    wicket 1 really is the bowler's first Test wicket (left-censoring rule).
    """
    eligible = career_wkts[(career_wkts >= n_wickets) & (first_test >= FULL_COVERAGE_FROM)].index
    w = df[df['bowler_id'].isin(eligible)].copy()
    w['wickets_taken'] = w.groupby('bowler_id')['is_wicket'].cumsum()
    w = w[w['wickets_taken'] - w['is_wicket'] < n_wickets].copy()
    # Halves for the split-half test: wickets 1..N/2 and N/2+1..N
    w['half'] = np.where(w['wickets_taken'] - w['is_wicket'] < n_wickets // 2, 1, 2)
    assert (w.groupby('bowler_id')['is_wicket'].sum() == n_wickets).all()
    assert (w[w['half'] == 1].groupby('bowler_id')['is_wicket'].sum() == n_wickets // 2).all()
    return w

win = build_windows(WICKET_WINDOW)

def summarise(w):
    s = w.groupby('bowler_id').agg(
        bowler=('bowler', 'first'), team=('bowling_team', 'first'), bowler_type=('bowler_type', 'first'),
        bowler_arm=('bowler_arm', 'first'), first_test=('date', 'min'), tests=('match_id', 'nunique'),
        runs=('bowler_runs', 'sum'), wkts=('is_wicket', 'sum'), legal=('is_legal', 'sum'))
    s['average'] = s['runs'] / s['wkts']
    s['strike_rate'] = s['legal'] / s['wkts']
    s['economy'] = 6 * s['runs'] / s['legal']
    assert np.allclose(s['average'], s['strike_rate'] * s['economy'] / 6)
    return s

bowlers = summarise(win)
dob = bowlers.index.map(player_styles['date_of_birth'])
bowlers['age_at_debut'] = (bowlers['first_test'] - pd.Series(dob, index=bowlers.index)).dt.days / 365.25
print(f'{len(bowlers)} bowlers reached {WICKET_WINDOW} Test wickets with a first Test on or after '
      f'{FULL_COVERAGE_FROM.date()} ({(bowlers.bowler_type == "spin").sum()} spin, '
      f'{(bowlers.bowler_type == "pace").sum()} pace, {(bowlers.bowler_type == "unknown").sum()} unknown)')
print(f'Average over the first {WICKET_WINDOW}: median {bowlers.average.median():.1f}, '
      f'range {bowlers.average.min():.1f}-{bowlers.average.max():.1f}')
bowlers.sort_values('average')[['bowler', 'team', 'bowler_type', 'tests', 'average', 'strike_rate', 'economy']].head(8)
