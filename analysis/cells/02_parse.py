PARSE_CACHE = CACHE_DIR / 'test_deliveries.pkl'

def parse_tests(json_dir):
    deliveries, dismissals, matches = [], [], []

    for file_path in sorted(json_dir.glob('*.json')):
        with open(file_path, 'r') as f:
            match_data = json.load(f)

        info = match_data.get('info', {})
        teams = info.get('teams', [])
        if info.get('match_type') != 'Test' or info.get('team_type') != 'international':
            continue
        if not set(teams) <= NATIONAL_TEAMS:
            continue

        match_id = int(file_path.stem)
        registry = info.get('registry', {}).get('people', {})
        outcome = info.get('outcome', {})
        toss = info.get('toss', {})
        umpires = info.get('officials', {}).get('umpires', [])

        matches.append({
            'match_id': match_id,
            'test_number': info.get('match_type_number'),
            'date': info.get('dates', [None])[0],
            'n_days_listed': len(info.get('dates', [])),
            'venue': info.get('venue'),
            'city': info.get('city'),
            'event': (info.get('event') or {}).get('name'),
            'team_1': teams[0],
            'team_2': teams[1],
            'toss_winner': toss.get('winner'),
            'toss_decision': toss.get('decision'),
            'umpire_1': umpires[0] if len(umpires) > 0 else None,
            'umpire_2': umpires[1] if len(umpires) > 1 else None,
            'winner': outcome.get('winner'),
            'result': outcome.get('result', 'win' if outcome.get('winner') else None),
        })

        for innings_num, innings in enumerate(match_data.get('innings', []), start=1):
            batting_team = innings.get('team')
            bowling_team = [t for t in teams if t != batting_team][0]
            declared = int(bool(innings.get('declared')))

            for over in innings.get('overs', []):
                over_num = over.get('over')

                for ball_num, delivery in enumerate(over.get('deliveries', []), start=1):
                    extras = delivery.get('extras', {})
                    runs = delivery.get('runs', {})
                    wickets = delivery.get('wickets', [])
                    review = delivery.get('review', {})
                    bowler_wicket = next((w for w in wickets if w.get('kind') in BOWLER_WICKET_KINDS), None)
                    first_wicket = wickets[0] if wickets else None
                    w = bowler_wicket or first_wicket or {}

                    deliveries.append({
                        'match_id': match_id,
                        'batting_team': batting_team,
                        'bowling_team': bowling_team,
                        'innings': innings_num,
                        'innings_declared': declared,
                        'over': over_num,
                        'ball': ball_num,
                        'bowler_id': registry.get(delivery.get('bowler')),
                        'bowler': delivery.get('bowler'),
                        'batter_id': registry.get(delivery.get('batter')),
                        'batter': delivery.get('batter'),
                        'non_striker_id': registry.get(delivery.get('non_striker')),
                        'runs_batter': runs.get('batter', 0),
                        'runs_total': runs.get('total', 0),
                        'wides': extras.get('wides', 0),
                        'noballs': extras.get('noballs', 0),
                        'byes': extras.get('byes', 0),
                        'legbyes': extras.get('legbyes', 0),
                        'penalty': extras.get('penalty', 0),
                        'is_wicket': int(bowler_wicket is not None),
                        'any_dismissal': int(any(x.get('kind') not in NON_DISMISSAL_KINDS for x in wickets)),
                        'wicket_kind': w.get('kind'),
                        'player_out_id': registry.get(w.get('player_out')),
                        'fielder': (w.get('fielders') or [{}])[0].get('name'),
                        'fielder_sub': int(bool((w.get('fielders') or [{}])[0].get('substitute'))),
                        'review_by': review.get('by'),
                        'review_decision': review.get('decision'),
                        'review_umpires_call': int(bool(review.get('umpires_call'))),
                    })

                    for x in wickets:
                        dismissals.append({
                            'match_id': match_id, 'innings': innings_num, 'over': over_num, 'ball': ball_num,
                            'player_out_id': registry.get(x.get('player_out')), 'kind': x.get('kind'),
                        })

    matches = pd.DataFrame(matches)
    matches['date'] = pd.to_datetime(matches['date'])
    df = pd.DataFrame(deliveries).merge(matches[['match_id', 'date', 'venue']], on='match_id')
    df = df.sort_values(['date', 'match_id', 'innings', 'over', 'ball']).reset_index(drop=True)
    df['seq'] = np.arange(len(df))
    dismissals = pd.DataFrame(dismissals)
    return df, dismissals, matches


if PARSE_CACHE.exists():
    with open(PARSE_CACHE, 'rb') as f:
        df, dismissals, matches = pickle.load(f)
else:
    df, dismissals, matches = parse_tests(JSON_DIR)
    with open(PARSE_CACHE, 'wb') as f:
        pickle.dump((df, dismissals, matches), f)

print(f'{len(matches)} international Tests, {len(df):,} deliveries')
print('Date range:', matches['date'].min().date(), 'to', matches['date'].max().date())
# Tests missing from Cricsheet since the cutoff: gaps in the official ICC Test numbering (mostly Afghanistan's
# Tests, which Cricsheet withholds). A bowler who played one has those wickets skipped in their window.
test_nums = matches.loc[matches['date'] >= FULL_COVERAGE_FROM, 'test_number'].dropna().astype(int)
N_TESTS_SINCE_CUTOFF = int(test_nums.max() - test_nums.min() + 1)
N_MISSING_TESTS = N_TESTS_SINCE_CUTOFF - test_nums.nunique()
print(f'Tests missing since {FULL_COVERAGE_FROM.year}: {N_MISSING_TESTS} of {N_TESTS_SINCE_CUTOFF} by ICC Test number')
