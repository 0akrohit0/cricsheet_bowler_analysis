def window_summary(n_wickets, by_type=None, n_boot=300):
    """Re-run the core results for one bowler type (or the whole window): noise share, variance split
    across parts, and split-half reliability/prediction of the three skill measures."""
    w = build_windows(n_wickets)
    w = w[w['bowler_type'].eq(by_type)] if by_type else w
    xr_, xw_, bm_ = attribute(w)
    c_, order_ = pd.factorize(bm_['bowler_id'])
    base_, xavg_, phi_, act_ = decompose(xr_, xw_, bm_, c_)
    parts = {g: phi_[:, i] for i, g in enumerate(GROUP_NAMES)}
    parts['dealt'] = sum(parts[g] for g in DEALT); parts['shaped'] = sum(parts[g] for g in SHAPED)
    parts['bowler_effect'] = act_ - xavg_; parts['baseline (pace or spin)'] = base_

    rows_ = [np.flatnonzero(c_ == i) for i in range(len(order_))]
    bparts = {k: [] for k in parts}; bact = []
    for _ in range(n_boot):
        take = np.concatenate([RNG.choice(r, size=len(r), replace=True) for r in rows_])
        b_base, b_x, b_phi, b_act = decompose(xr_[:, take], xw_[:, take], bm_.iloc[take], c_[take])
        bp = {g: b_phi[:, i] for i, g in enumerate(GROUP_NAMES)}
        bp['dealt'] = sum(bp[g] for g in DEALT); bp['shaped'] = sum(bp[g] for g in SHAPED)
        bp['bowler_effect'] = b_act - b_x; bp['baseline (pace or spin)'] = b_base
        for k in parts: bparts[k].append(bp[k])
        bact.append(b_act)
    bact = np.array(bact); bparts = {k: np.array(v) for k, v in bparts.items()}
    true_var = act_.var(ddof=1) - noise_cov(bact, bact)
    out = {'n_bowlers': len(order_), 'share real': true_var / act_.var(ddof=1)}
    for k in ['baseline (pace or spin)', 'dealt', 'shaped', 'bowler_effect'] + GROUP_NAMES:
        # When almost all of the spread is noise, these ratios divide by ~0 and mean nothing
        share = (np.cov(parts[k], act_)[0, 1] - noise_cov(bparts[k], bact)) / true_var
        out[f'real share: {k}'] = share if out['share real'] >= 0.15 else np.nan

    extra = [c for c in ['dots_before', 'caught_keeper'] if c not in w.columns]
    wd_ = w.merge(ctx[['seq', 'p_wkt', 'mu_run']], on='seq').merge(df[['seq'] + extra], on='seq')
    a1, a2 = components(wd_[wd_['half'] == 1]), components(wd_[wd_['half'] == 2])
    for comp in ['overall skill', 'wicket-taking skill', 'run-control skill']:
        out[f'reliability: {comp}'] = stats.spearmanr(a1[comp], a2.loc[a1.index, comp])[0]
        out[f'predicts 2nd half: {comp}'] = stats.spearmanr(a1[comp], a2.loc[a1.index, 'overall skill'])[0]
    out['reliability: raw average'] = stats.spearmanr(a1['average'], a2.loc[a1.index, 'average'])[0]
    return pd.Series(out)

sensitivity = pd.DataFrame({
    f'first {WICKET_WINDOW} (main)': window_summary(WICKET_WINDOW),
    f'first {WICKET_WINDOW}, pace only': window_summary(WICKET_WINDOW, 'pace'),
    f'first {WICKET_WINDOW}, spin only': window_summary(WICKET_WINDOW, 'spin'),
})
sensitivity.round(2)
