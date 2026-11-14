# ---- basic per-ball quantities -------------------------------------------------------------
df['is_legal'] = ((df['wides'] == 0) & (df['noballs'] == 0)).astype(int)
df['ball_faced'] = (df['wides'] == 0).astype(int)          # no-balls count as faced, wides don't
df['bowler_runs'] = df['runs_total'] - df['byes'] - df['legbyes'] - df['penalty']
df['year'] = df['date'].dt.year

# ---- batting position: order of first appearance at the crease in each innings -------------
appear = pd.concat([
    df[['match_id', 'innings', 'seq', 'batter_id']].rename(columns={'batter_id': 'pid'}),
    df[['match_id', 'innings', 'seq', 'non_striker_id']].rename(columns={'non_striker_id': 'pid'}),
]).sort_values('seq').drop_duplicates(['match_id', 'innings', 'pid'])
appear['batting_position'] = appear.groupby(['match_id', 'innings']).cumcount() + 1
df = df.merge(appear[['match_id', 'innings', 'pid', 'batting_position']]
              .rename(columns={'pid': 'batter_id'}), on=['match_id', 'innings', 'batter_id'], how='left')

# ---- batter state within the innings, before this ball -------------------------------------
g = df.groupby(['match_id', 'innings', 'batter_id'])
df['batter_balls_before'] = g['ball_faced'].cumsum() - df['ball_faced']
df['batter_runs_before'] = g['runs_batter'].cumsum() - df['runs_batter']

# ---- batter quality entering the match (prior Tests in the data only) ----------------------
outs = (dismissals[~dismissals['kind'].isin(NON_DISMISSAL_KINDS)]
        .groupby(['match_id', 'player_out_id']).size().rename('outs').reset_index()
        .rename(columns={'player_out_id': 'batter_id'}))
batter_match = (df.groupby(['batter_id', 'match_id'])
                .agg(runs=('runs_batter', 'sum'), balls=('ball_faced', 'sum'), date=('date', 'first'))
                .reset_index().merge(outs, on=['match_id', 'batter_id'], how='left'))
batter_match['outs'] = batter_match['outs'].fillna(0)
batter_match = batter_match.sort_values(['batter_id', 'date', 'match_id'])
for c in ['runs', 'balls', 'outs']:
    batter_match[f'prior_{c}'] = batter_match.groupby('batter_id')[c].cumsum() - batter_match[c]
batter_match['prior_tests'] = batter_match.groupby('batter_id').cumcount()
df = df.merge(batter_match[['batter_id', 'match_id', 'prior_runs', 'prior_balls', 'prior_outs', 'prior_tests']]
              .rename(columns={'prior_tests': 'batter_prior_tests'}), on=['batter_id', 'match_id'], how='left')

def position_band(pos):
    return np.select([pos <= 2, pos <= 4, pos <= 7], ['opener', 'top 3-4', 'middle 5-7'], 'tail 8-11')

df['batter_band'] = position_band(df['batting_position'])
# Shrink toward the typical average for the batting position (5 pseudo-dismissals), as in the old notebook
band_avg = df.groupby('batter_band').apply(
    lambda x: x['runs_batter'].sum() / x['any_dismissal'].sum(), include_groups=False)
K_SHRINK = 5
df['batter_prior_avg'] = ((df['prior_runs'] + K_SHRINK * df['batter_band'].map(band_avg))
                          / (df['prior_outs'] + K_SHRINK))
df['batter_prior_sr'] = ((df['prior_runs'] + 0.5 * 300) / (df['prior_balls'] + 300) * 100)   # shrunk toward 50

# Opposition line-up strength, fixed before the match: mean pre-match average of the batting side's best 7.
# This is what the bowler is dealt. Which of those batters is at the crease on a given ball is partly
# the bowler's own doing (dismiss the top order and you bowl at the tail), so it is kept separate.
bat_xi = df.groupby(['match_id', 'batting_team', 'batter_id'])['batter_prior_avg'].first().reset_index()
lineup = (bat_xi.sort_values('batter_prior_avg', ascending=False).groupby(['match_id', 'batting_team'])
          .head(7).groupby(['match_id', 'batting_team'])['batter_prior_avg'].mean().rename('lineup_avg'))
df = df.merge(lineup.reset_index(), on=['match_id', 'batting_team'], how='left')
df['batter_vs_lineup'] = df['batter_prior_avg'] - df['lineup_avg']

# ---- batter and bowler metadata (scraped from Cricinfo by scrape_player_styles.py) ---------
player_styles = pd.read_csv('player_styles.csv').drop_duplicates('identifier').set_index('identifier')
player_styles['date_of_birth'] = pd.to_datetime(player_styles['date_of_birth'], errors='coerce', format='mixed')

def parse_batting_hand(s):
    if not isinstance(s, str): return None
    s = s.lower()
    return 'left' if 'left' in s else ('right' if 'right' in s else None)

SPIN_TYPES = ('offbreak', 'legbreak', 'orthodox', 'googly', 'chinaman', 'unorthodox', 'wrist')

def parse_bowling_style(s):
    """Return (arm, is_spinner) from the first listed bowling style, e.g. 'right-arm fast-medium, legbreak'."""
    if not isinstance(s, str): return (None, None)
    first = s.split(',')[0].lower()
    arm = 'left' if 'left-arm' in first or first.startswith('slow left') else 'right'
    return (arm, int(any(t in first for t in SPIN_TYPES) or first.startswith('slow left')))

df['batter_hand'] = df['batter_id'].map(player_styles['batting_style']).map(parse_batting_hand).fillna('unknown')

# ---- ball age, phase and pitch wear --------------------------------------------------------
# The new ball is due after 80 overs; assume it is taken then (the data doesn't record it)
df['ball_age_overs'] = np.where(df['over'] < 80, df['over'], (df['over'] - 80) % 80)
df['second_new_ball'] = (df['over'] >= 80).astype(int)
df['match_ball'] = df.groupby('match_id')['is_legal'].cumsum() - df['is_legal']
df['match_over'] = df['match_ball'] // 6            # overs bowled in the match before this ball (~90 per day)

# ---- match state, before this ball ---------------------------------------------------------
df['innings_runs_before'] = df.groupby(['match_id', 'innings'])['runs_total'].cumsum() - df['runs_total']
df['innings_wkts_before'] = df.groupby(['match_id', 'innings'])['any_dismissal'].cumsum() - df['any_dismissal']
inn_tot = df.groupby(['match_id', 'innings']).agg(team=('batting_team', 'first'), runs=('runs_total', 'sum')).reset_index()
prev = []
for mid, grp in inn_tot.groupby('match_id'):
    for _, r in grp.iterrows():
        earlier = grp[grp['innings'] < r['innings']]
        prev.append({'match_id': mid, 'innings': r['innings'],
                     'bat_prev_runs': earlier.loc[earlier['team'] == r['team'], 'runs'].sum(),
                     'bowl_prev_runs': earlier.loc[earlier['team'] != r['team'], 'runs'].sum()})
df = df.merge(pd.DataFrame(prev), on=['match_id', 'innings'], how='left')
# Bowling team's lead (positive = ahead). In the 4th innings this is runs still needed minus one.
df['bowling_lead'] = df['bowl_prev_runs'] - df['bat_prev_runs'] - df['innings_runs_before']
inn2_team = inn_tot[inn_tot['innings'] == 2].set_index('match_id')['team']
df['follow_on'] = ((df['innings'] == 3) & (df['batting_team'] == df['match_id'].map(inn2_team))).astype(int)

# ---- toss, venue country and home advantage ------------------------------------------------
matches['place'] = matches['city'].fillna(matches['venue'].str.split(',').str[-1].str.strip())
# Host country, in order of preference:
#   1. the event name ("India tour of Australia", "England in India Test Series")
#   2. the host most often named by events at the same place (covers trophy series like The Ashes)
#   3. the team in at least 75% of the place's Tests (3+ Tests needed)
# The UAE (Pakistan's and Afghanistan's adopted home) is treated as neutral.
def host_from_event(r):
    ev = r['event'] if isinstance(r['event'], str) else ''
    hits = [t for t in (r['team_1'], r['team_2']) if f'tour of {t}' in ev or f' in {t}' in ev]
    if not hits and ' v ' in ev:           # "Sri Lanka v Bangladesh": home side is named first
        hits = [t for t in (r['team_1'], r['team_2']) if ev.startswith(t)]
    return hits[0] if len(hits) == 1 else None
matches['host_event'] = matches.apply(host_from_event, axis=1)
host_place_event = matches.dropna(subset=['host_event']).groupby('place')['host_event'].agg(lambda s: s.mode().iloc[0])
long = pd.concat([matches[['match_id', 'place', 'team_1']].rename(columns={'team_1': 'team'}),
                  matches[['match_id', 'place', 'team_2']].rename(columns={'team_2': 'team'})])
n_place = matches.groupby('place').size()
share = long.groupby(['place', 'team']).size() / n_place
share = share[(share >= 0.75) & (share.index.get_level_values('place').map(n_place) >= 3)]
host_place_share = share.sort_values(ascending=False).reset_index().drop_duplicates('place').set_index('place')['team']
fallback = matches['place'].map(host_place_event).fillna(matches['place'].map(host_place_share))
fallback = fallback.where(fallback.eq(matches['team_1']) | fallback.eq(matches['team_2']))
is_uae = (matches['place'] + ' ' + matches['venue']).str.contains('Dubai|Sharjah|Abu Dhabi')
matches['host'] = matches['host_event'].fillna(fallback).where(~is_uae)
print('Tests treated as neutral:', matches['host'].isna().sum(), '-',
      sorted(matches.loc[matches['host'].isna(), 'place'].unique()))
df = df.merge(matches[['match_id', 'host', 'toss_winner', 'toss_decision', 'umpire_1', 'umpire_2']], on='match_id')
df['venue_for_bowler'] = np.select(
    [df['host'] == df['bowling_team'], df['host'] == df['batting_team']], ['home', 'away'], 'neutral')
df['host_country'] = df['host'].fillna('Neutral')
df['bowled_first_by_choice'] = ((df['toss_winner'] == df['bowling_team']) & (df['toss_decision'] == 'field')).astype(int)

# ---- officials and DRS ----------------------------------------------------------------------
drs_matches = set(df.loc[df['review_by'].notna(), 'match_id'])
df['drs_in_use'] = df['match_id'].isin(drs_matches).astype(int)
m_lbw = df.groupby('match_id').agg(lbw=('wicket_kind', lambda s: (s == 'lbw').sum()), balls=('is_legal', 'sum'))
m_ump = matches.set_index('match_id')[['umpire_1', 'umpire_2']].join(m_lbw)
ump_long = pd.concat([m_ump[['umpire_1', 'lbw', 'balls']].rename(columns={'umpire_1': 'ump'}),
                      m_ump[['umpire_2', 'lbw', 'balls']].rename(columns={'umpire_2': 'ump'})]).dropna(subset=['ump'])
ump_tot = ump_long.groupby('ump')[['lbw', 'balls']].sum()
league_lbw = m_lbw['lbw'].sum() / m_lbw['balls'].sum()
def ump_rate(u, mid):   # umpire's LBW rate in all OTHER matches, shrunk toward the league rate
    if pd.isna(u) or u not in ump_tot.index: return league_lbw
    lbw = ump_tot.at[u, 'lbw'] - m_ump.at[mid, 'lbw']; balls = ump_tot.at[u, 'balls'] - m_ump.at[mid, 'balls']
    return (lbw + league_lbw * 20000) / (balls + 20000)
m_ump['umpire_lbw_rate'] = [np.mean([ump_rate(r.umpire_1, mid), ump_rate(r.umpire_2, mid)]) for mid, r in m_ump.iterrows()]
df['umpire_lbw_index'] = df['match_id'].map(m_ump['umpire_lbw_rate']) / league_lbw

# ---- bowler usage: opener, spells, workload ------------------------------------------------
bo = (df.groupby(['match_id', 'innings', 'bowler_id', 'over'], sort=False)
      .agg(seq=('seq', 'first')).reset_index().sort_values('seq'))
bo['gap'] = bo.groupby(['match_id', 'innings', 'bowler_id'])['over'].diff()
bo['new_spell'] = (bo['gap'].isna() | (bo['gap'] > 2)).astype(int)
bo['spell_no'] = bo.groupby(['match_id', 'innings', 'bowler_id'])['new_spell'].cumsum()
bo['over_in_spell'] = bo.groupby(['match_id', 'innings', 'bowler_id', 'spell_no']).cumcount() + 1
bo['match_overs_before'] = bo.groupby(['match_id', 'bowler_id']).cumcount()
openers = bo[bo['over'] <= 1].groupby(['match_id', 'innings'])['bowler_id'].apply(set)
bo['is_opener'] = [int(b in openers.get((m, i), set())) for m, i, b in zip(bo['match_id'], bo['innings'], bo['bowler_id'])]
# Bowler at the other end: whoever bowled the previous over of the innings
inn_overs = bo.sort_values('seq').groupby(['match_id', 'innings'])
bo['partner_id'] = inn_overs['bowler_id'].shift(1)
bo.loc[bo['partner_id'] == bo['bowler_id'], 'partner_id'] = None
df = df.merge(bo[['match_id', 'innings', 'bowler_id', 'over', 'spell_no', 'over_in_spell',
                  'match_overs_before', 'is_opener', 'partner_id']],
              on=['match_id', 'innings', 'bowler_id', 'over'], how='left')

# Partner quality: the partner's bowling average entering the match (shrunk with 10 pseudo-wickets)
bm = (df.groupby(['bowler_id', 'match_id']).agg(runs=('bowler_runs', 'sum'), wkts=('is_wicket', 'sum'), date=('date', 'first'))
      .reset_index().sort_values(['bowler_id', 'date', 'match_id']))
for c in ['runs', 'wkts']:
    bm[f'prior_{c}'] = bm.groupby('bowler_id')[c].cumsum() - bm[c]
LEAGUE_AVG = df['bowler_runs'].sum() / df['is_wicket'].sum()
bm['prior_bowl_avg'] = (bm['prior_runs'] + 10 * LEAGUE_AVG) / (bm['prior_wkts'] + 10)
df = df.merge(bm[['bowler_id', 'match_id', 'prior_bowl_avg']].rename(
    columns={'bowler_id': 'partner_id', 'prior_bowl_avg': 'partner_prior_avg'}), on=['partner_id', 'match_id'], how='left')
df['partner_prior_avg'] = df['partner_prior_avg'].fillna(LEAGUE_AVG)

# ---- bowler profile --------------------------------------------------------------------------
arm_spin = df['bowler_id'].map(player_styles['bowling_style']).map(parse_bowling_style)
df['bowler_arm'] = arm_spin.str[0].fillna('unknown')
df['is_spinner'] = arm_spin.str[1]
df['bowler_type'] = np.select([df['is_spinner'] == 1, df['is_spinner'] == 0], ['spin', 'pace'], 'unknown')

df = df.sort_values('seq').reset_index(drop=True)
print(f'League runs per wicket: {LEAGUE_AVG:.2f}')
print('Bowlers missing a style:', df.loc[df['bowler_type'] == 'unknown', 'bowler_id'].nunique(),
      'of', df['bowler_id'].nunique(), '| share of balls:', round((df['bowler_type'] == 'unknown').mean(), 4))
print(df['venue_for_bowler'].value_counts(normalize=True).round(3))
