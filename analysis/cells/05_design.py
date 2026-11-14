# The context model is trained on every delivery bowled in Tests from FULL_COVERAGE_FROM onward,
# by every bowler, not just the 109 in the study.
ctx = df[(df['date'] >= FULL_COVERAGE_FROM) & (df['bowler_type'] != 'unknown')].reset_index(drop=True)

def cut(s, edges, labels=None):
    return pd.cut(s, edges, labels=labels, right=False).astype(str)

def make_bins(d):
    """Discretise every context variable. Interactions with bowler type are kept inside their own group."""
    t = d['bowler_type']
    b = pd.DataFrame(index=d.index)
    # Opposition line-up strength (dealt)
    b['lineup'] = cut(d['lineup_avg'], [0, 28, 31, 34, 37, 40, 43, 46, np.inf])
    # Who is at the crease, relative to that line-up (shaped by the bowler and team)
    b['bat_rel'] = cut(d['batter_vs_lineup'], [-np.inf, -25, -15, -8, -3, 3, 8, 15, np.inf])
    b['bat_sr'] = cut(d['batter_prior_sr'], [0, 42, 47, 52, 57, 62, np.inf])
    b['bat_exp'] = cut(d['batter_prior_tests'], [0, 1, 6, 16, 36, 71, np.inf])
    b['bat_band'] = d['batter_band']
    # Hand matchup as same side / opposite side, so it doesn't duplicate the bowler's arm
    same_side = np.where((d['batter_hand'] == 'left') == (d['bowler_arm'] == 'left'), 'same', 'opposite')
    b['bat_hand_x_type'] = np.where(d['batter_hand'] == 'unknown', 'unknown', same_side) + '|' + t
    # How set the batter is
    b['set'] = cut(d['batter_balls_before'], [0, 1, 6, 11, 21, 41, 81, 151, np.inf])
    # Match phase: which innings, which day
    b['innings_x_type'] = d['innings'].astype(str) + '|' + t
    b['day_x_type'] = cut(d['match_over'], [0, 90, 180, 270, 360, np.inf]) + '|' + t
    # Match state
    b['lead_x_inn'] = cut(d['bowling_lead'], [-np.inf, -300, -150, -50, 0, 50, 150, 300, np.inf]) + '|' + d['innings'].astype(str)
    b['wkts_down'] = d['innings_wkts_before'].clip(upper=9).astype(str)
    b['follow_on'] = d['follow_on'].astype(str)
    # Venue and home advantage
    b['home_x_type'] = d['venue_for_bowler'] + '|' + t
    b['country_x_type'] = d['host_country'] + '|' + t
    b['toss_field'] = d['bowled_first_by_choice'].astype(str)
    # Era and officiating
    b['era'] = cut(d['year'], [2007, 2010, 2013, 2016, 2019, 2022, 2030])
    b['drs'] = d['drs_in_use'].astype(str)
    b['umpire_lbw'] = cut(d['umpire_lbw_index'], [0, 0.95, 1.0, 1.05, np.inf])
    # Role and usage (captain's decisions): ball age, opening, spells, workload
    b['ball_age_x_type'] = cut(d['ball_age_overs'], [0, 6, 11, 21, 36, 51, 66, 81]) + '|' + t
    b['new_ball2'] = d['second_new_ball'].astype(str)
    b['opener_x_type'] = d['is_opener'].astype(str) + '|' + t
    b['spell_over_x_type'] = cut(d['over_in_spell'], [1, 2, 3, 5, 7, 10, np.inf]) + '|' + t
    b['spell_no'] = d['spell_no'].clip(upper=6).astype(str)
    b['workload'] = cut(d['match_overs_before'], [0, 10, 20, 30, 40, np.inf])
    # Bowling partner at the other end
    b['partner'] = cut(d['partner_prior_avg'], [0, 26, 29, 32, 35, 38, np.inf])
    # Bowler type and arm (the reference is type-matched, so only the arm varies within a type)
    b['type'] = t + '|' + d['bowler_arm']
    return b

# "Dealt": fixed before the ball is bowled and outside the bowler's control.
# "Shaped": situations that partly result from the bowler's (and team's) own success or the captain's
# reading of it, so they are reported separately and never counted as luck.
GROUPS = {
    'Opposition line-up':  ['lineup'],
    'Venue & home':        ['home_x_type', 'country_x_type', 'toss_field'],
    'Era & umpires':       ['era', 'drs', 'umpire_lbw'],
    'Match phase':         ['innings_x_type', 'day_x_type'],
    'Bowling partner':     ['partner'],
    'Bowling arm':         ['type'],
    "Who's at the crease": ['bat_rel', 'bat_sr', 'bat_exp', 'bat_band', 'bat_hand_x_type'],
    'Batter set or new':   ['set'],
    'Match state':         ['lead_x_inn', 'wkts_down', 'follow_on'],
    'Role & usage':        ['ball_age_x_type', 'new_ball2', 'opener_x_type', 'spell_over_x_type', 'spell_no', 'workload'],
}
DEALT = ['Opposition line-up', 'Venue & home', 'Era & umpires', 'Match phase', 'Bowling partner', 'Bowling arm']
SHAPED = ["Who's at the crease", 'Batter set or new', 'Match state', 'Role & usage']
GROUP_NAMES = list(GROUPS)
COL_GROUP = {c: g for g, cols in GROUPS.items() for c in cols}

bins = make_bins(ctx)
levels = {c: sorted(bins[c].unique()) for c in bins}

def one_hot(b):
    """Sparse one-hot matrix with a fixed column order, plus the group of each column."""
    mats, col_groups, names = [], [], []
    for c in bins.columns:
        cat = pd.Categorical(b[c], categories=levels[c])
        codes = cat.codes
        m = sparse.csr_matrix((np.ones(len(b)), (np.arange(len(b)), codes)), shape=(len(b), len(levels[c])))
        mats.append(m); col_groups += [COL_GROUP[c]] * len(levels[c]); names += [f'{c}={l}' for l in levels[c]]
    return sparse.hstack(mats).tocsr(), np.array(col_groups), names

X_ctx, col_group, col_names = one_hot(bins)
y_wkt = ctx['is_wicket'].to_numpy()
y_runs = ctx['bowler_runs'].to_numpy().astype(float)
print(f'Context model: {X_ctx.shape[0]:,} deliveries x {X_ctx.shape[1]} indicator columns in {len(GROUPS)} groups')
