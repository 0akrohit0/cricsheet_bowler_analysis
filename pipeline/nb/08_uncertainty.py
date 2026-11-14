# Resample each bowler's Tests with replacement (the bowler-match sums are already computed per coalition)
B_MATCH = 500
bm_codes = codes
rows_of = [np.flatnonzero(bm_codes == i) for i in range(len(bowler_order))]
boot_phi = np.zeros((B_MATCH, len(bowler_order), G))
boot_actual = np.zeros((B_MATCH, len(bowler_order)))
boot_xavg = np.zeros_like(boot_actual)
for b in range(B_MATCH):
    take = np.concatenate([RNG.choice(r, size=len(r), replace=True) for r in rows_of])
    _, xa, ph, ac = decompose(xr[:, take], xw[:, take], bm.iloc[take], bm_codes[take])
    boot_phi[b], boot_actual[b], boot_xavg[b] = ph, ac, xa

boot_effect = boot_actual - boot_xavg

def put_interval(name, boot):
    # Bootstrap arrays are in bowler_order; att is indexed by bowler_id in a different order
    lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
    att[f'{name}_lo'] = pd.Series(lo, index=bowler_order)
    att[f'{name}_hi'] = pd.Series(hi, index=bowler_order)

put_interval('bowler_effect', boot_effect)
put_interval('actual', boot_actual)
for gi, g in enumerate(GROUP_NAMES):
    put_interval(g, boot_phi[:, :, gi])
assert (att['bowler_effect_lo'] <= att['bowler_effect']).all() and (att['bowler_effect'] <= att['bowler_effect_hi']).all()

# How much of the spread is just the luck of 50 wickets? Subtract the average sampling variance.
noise = pd.Series({
    'actual average': boot_actual.var(0).mean(),
    'context-expected (xAvg)': boot_xavg.var(0).mean(),
    'bowler effect': boot_effect.var(0).mean(),
})
observed = pd.Series({'actual average': att['actual'].var(), 'context-expected (xAvg)': att['xAvg'].var(),
                      'bowler effect': att['bowler_effect'].var()})
signal = pd.DataFrame({'observed sd': np.sqrt(observed), 'sampling-noise sd': np.sqrt(noise),
                       'true sd (noise removed)': np.sqrt((observed - noise).clip(lower=0))})
signal['share of variance that is real'] = 1 - noise / observed
signal.round(2)

# Share of the REAL spread in averages that each part accounts for.
# cov(part, actual) splits var(actual) exactly across the parts; subtracting the within-bowler
# bootstrap covariance removes the part that is only shared sampling noise.
gi_of = {g: i for i, g in enumerate(GROUP_NAMES)}
boot_parts = {g: boot_phi[:, :, gi_of[g]] for g in GROUP_NAMES}
boot_parts['dealt'] = sum(boot_parts[g] for g in DEALT)
boot_parts['shaped'] = sum(boot_parts[g] for g in SHAPED)
boot_parts['bowler_effect'] = boot_effect
boot_parts['baseline (pace or spin)'] = boot_actual - boot_effect - boot_parts['dealt'] - boot_parts['shaped']
att['baseline (pace or spin)'] = att['baseline']

def noise_cov(a, b):
    return np.mean([np.cov(a[:, i], b[:, i])[0, 1] for i in range(a.shape[1])])

true_var = att['actual'].var() - noise_cov(boot_actual, boot_actual)
share_rows = []
for part in ['baseline (pace or spin)', 'dealt', 'shaped', 'bowler_effect'] + GROUP_NAMES:
    cov_obs = np.cov(att[part], att['actual'])[0, 1]
    cov_true = cov_obs - noise_cov(boot_parts[part], boot_actual)
    share_rows.append({'part': part, 'share of observed variance': cov_obs / att['actual'].var(),
                       'share of real variance': cov_true / true_var})
variance_shares = pd.DataFrame(share_rows).set_index('part')
variance_shares.round(3)
