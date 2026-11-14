
# Cross-fitting: every bowler's deliveries are scored by models that never saw that bowler.
N_FOLDS = 5
fold_of_bowler = {b: i % N_FOLDS for i, b in enumerate(RNG.permutation(ctx['bowler_id'].unique()))}
fold = ctx['bowler_id'].map(fold_of_bowler).to_numpy()

# Per-row linear predictor split by group, from the model of the row's own fold
eta_wkt = np.zeros((len(ctx), len(GROUP_NAMES)))
eta_run = np.zeros((len(ctx), len(GROUP_NAMES)))
icpt_wkt, icpt_run = np.zeros(len(ctx)), np.zeros(len(ctx))
glm_coefs, glm_models = [], []

for k in range(N_FOLDS):
    tr, te = fold != k, fold == k
    # Wickets are rare (about 1.6% of balls), so a log-link Poisson model is effectively a logistic one,
    # and the log link lets the attribution below be computed exactly.
    pw = PoissonRegressor(alpha=1e-6, max_iter=500, tol=1e-6).fit(X_ctx[tr], y_wkt[tr])
    pr = PoissonRegressor(alpha=1e-6, max_iter=500, tol=1e-6).fit(X_ctx[tr], y_runs[tr])
    for gi, g in enumerate(GROUP_NAMES):
        cols = col_group == g
        eta_wkt[te, gi] = X_ctx[te][:, cols] @ pw.coef_[cols]
        eta_run[te, gi] = X_ctx[te][:, cols] @ pr.coef_[cols]
    icpt_wkt[te], icpt_run[te] = pw.intercept_, pr.intercept_
    glm_models.append((pw, pr))
    glm_coefs.append(pd.DataFrame({'fold': k, 'col': col_names, 'group': col_group, 'b_wkt': pw.coef_, 'b_run': pr.coef_}))
    print(f'fold {k}: fitted on {tr.sum():,} deliveries')

ctx['p_wkt'] = np.exp(icpt_wkt + eta_wkt.sum(1))
ctx['mu_run'] = np.exp(icpt_run + eta_run.sum(1))

# ---- How good is the context model? Compare with a constant and with gradient boosting --------
NUM_FEATURES = ['lineup_avg', 'batter_prior_avg', 'batter_prior_sr', 'batter_prior_tests', 'batting_position', 'batter_balls_before',
                'ball_age_overs', 'second_new_ball', 'innings', 'match_over', 'bowling_lead', 'innings_wkts_before',
                'follow_on', 'bowled_first_by_choice', 'year', 'drs_in_use', 'umpire_lbw_index', 'is_opener',
                'over_in_spell', 'spell_no', 'match_overs_before', 'partner_prior_avg']
CAT_FEATURES = ['batter_hand', 'venue_for_bowler', 'host_country', 'bowler_type', 'bowler_arm']
Xg = ctx[NUM_FEATURES].copy()
for c in CAT_FEATURES:
    Xg[c] = ctx[c].astype('category')
gbm_p, gbm_mu = np.zeros(len(ctx)), np.zeros(len(ctx))
for k in range(N_FOLDS):
    tr, te = fold != k, fold == k
    gc = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
                                        categorical_features='from_dtype', random_state=0).fit(Xg[tr], y_wkt[tr])
    gr = HistGradientBoostingRegressor(loss='poisson', max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
                                       categorical_features='from_dtype', random_state=0).fit(Xg[tr], y_runs[tr])
    gbm_p[te], gbm_mu[te] = gc.predict_proba(Xg[te])[:, 1], gr.predict(Xg[te])

base_p, base_mu = np.full(len(ctx), y_wkt.mean()), np.full(len(ctx), y_runs.mean())
model_fit = pd.DataFrame({
    'wicket log-loss': [log_loss(y_wkt, base_p), log_loss(y_wkt, ctx['p_wkt'].clip(upper=1 - 1e-9)), log_loss(y_wkt, gbm_p)],
    'runs Poisson deviance': [mean_poisson_deviance(y_runs, base_mu), mean_poisson_deviance(y_runs, ctx['mu_run']),
                              mean_poisson_deviance(y_runs, gbm_mu)],
}, index=['constant', 'additive GLM (used)', 'gradient boosting'])
model_fit['wicket: % of loss explained'] = 100 * (1 - model_fit['wicket log-loss'] / model_fit.loc['constant', 'wicket log-loss'])
model_fit['runs: % of deviance explained'] = 100 * (1 - model_fit['runs Poisson deviance'] / model_fit.loc['constant', 'runs Poisson deviance'])
print(f"Calibration: predicted wickets {ctx['p_wkt'].sum():,.0f} vs actual {y_wkt.sum():,}; "
      f"predicted runs {ctx['mu_run'].sum():,.0f} vs actual {y_runs.sum():,.0f}")
model_fit.round(4)
