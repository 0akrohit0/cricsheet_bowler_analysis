def records(frame, index_name=None):
    f = frame.reset_index() if index_name else frame
    if index_name:
        f = f.rename(columns={f.columns[0]: index_name})
    return json.loads(f.to_json(orient='records', double_precision=4))

EFFECT_VARS = ['home_x_type', 'country_x_type', 'lineup', 'partner', 'era', 'drs', 'umpire_lbw', 'toss_field',
               'innings_x_type', 'day_x_type', 'ball_age_x_type', 'new_ball2', 'opener_x_type', 'spell_over_x_type',
               'workload', 'set', 'bat_rel', 'bat_band', 'bat_hand_x_type', 'wkts_down', 'type']
white_ball = pd.concat({'all': wb_vs_test, 'odi10': wb_vs_test_10}, axis=1)
white_ball.columns = [f'{a}_{b}' for a, b in white_ball.columns]
bowler_out = att.join(bowlers[['tests', 'strike_rate', 'economy', 'first_test']]).join(
    full[['wicket-taking skill', 'run-control skill', 'overall skill']])
bowler_out['first_test'] = bowler_out['first_test'].dt.strftime('%Y-%m-%d')

results = {
    'meta': {
        'n_tests': int(matches['match_id'].nunique()),
        'n_tests_model': int(ctx['match_id'].nunique()),
        'n_deliveries_model': int(len(ctx)),
        'n_bowlers_model': int(ctx['bowler_id'].nunique()),
        'date_range': [str(matches['date'].min().date()), str(matches['date'].max().date())],
        'window': WICKET_WINDOW, 'data_end_year': int(matches['date'].max().year),
        'n_tests_since_cutoff': N_TESTS_SINCE_CUTOFF, 'n_missing_tests': int(N_MISSING_TESTS),
        'bowler_terms': True, 'calibration_pct': {k: float(v) for k, v in CALIBRATION.items()}, 'n_effect_refits': B_REFIT,
        'full_coverage_from': str(FULL_COVERAGE_FROM.date()),
        'n_bowlers': int(len(bowlers)), 'n_pace': int((bowlers.bowler_type == 'pace').sum()),
        'n_spin': int((bowlers.bowler_type == 'spin').sum()),
        'league_avg': float(LEAGUE_AVG),
        'baseline_by_type': att.groupby('bowler_type')['baseline'].mean().round(2).to_dict(),
        'raw_half_reliability': list(map(float, raw_rel)), 'dealt_half_reliability': list(map(float, ctx_rel)),
        'n_pre_debut_odi': int((profile['pre-debut ODIs'] > 0).sum()),
        'n_neutral_tests': int(matches['host'].isna().sum()),
        'groups': GROUPS, 'dealt': DEALT, 'shaped': SHAPED,
    },
    'model_fit': records(model_fit, 'model'),
    'signal': records(signal, 'quantity'),
    'variance_shares': records(variance_shares, 'part'),
    'bowlers': records(bowler_out, 'bowler_id'),
    'split_half': records(split, 'component'),
    'prediction': records(pred_table, 'features'),
    'r2_ceiling': float(R2_CEILING),
    'white_ball': records(white_ball, 'pair'),
    'n_odi10': int(has_odi.sum()),
    'effects': records(effects[effects['variable'].isin(EFFECT_VARS)]),
    'sensitivity': records(sensitivity, 'measure'),
}
with open(RESULTS_FILE, 'w') as f:
    json.dump(results, f, indent=1)
print('Wrote', RESULTS_FILE)
