# Effect of each level of each context variable on the average, holding everything else at typical
# conditions for that bowler type. Because both models are log-linear, for a variable c at level l:
#     wicket rate x  exp(b_wkt[l]) / E_type[exp(b_wkt[c])]      (strike-rate part)
#     run rate    x  exp(b_run[l]) / E_type[exp(b_run[c])]      (economy part)
#     average     x  run factor / wicket factor
# Intervals: refit both models on Tests resampled with replacement (balls within a match aren't independent).
B_REFIT = 200
match_codes, match_list = pd.factorize(ctx['match_id'])

def fit_full(weights=None):
    """Condition coefficients from the same models as 06_models (with bowler terms), on all deliveries."""
    return fit_glm(y_wkt, weights=weights).coef_, fit_glm(y_runs, weights=weights).coef_

col_var = np.array([n.split('=')[0] for n in col_names])
col_level = np.array([n.split('=', 1)[1] for n in col_names])
level_share = {t: np.asarray(X_ctx[type_code == ti].mean(0)).ravel() for ti, t in enumerate(TYPES)}

def level_effects(bw, br):
    out = []
    for var in bins.columns:
        idx = np.flatnonzero(col_var == var)
        for t in TYPES:
            w = level_share[t][idx]
            if w.sum() == 0: continue
            w = w / w.sum()
            ew = np.exp(bw[idx]) / (w * np.exp(bw[idx])).sum()
            er = np.exp(br[idx]) / (w * np.exp(br[idx])).sum()
            for j, lev in enumerate(col_level[idx]):
                if w[j] < 0.002: continue          # skip levels this type almost never meets
                out.append((var, lev, t, w[j], 100 * (er[j] / ew[j] - 1), 100 * (1 / ew[j] - 1), 100 * (er[j] - 1)))
    return pd.DataFrame(out, columns=['variable', 'level', 'bowler_type', 'share', 'avg_pct', 'sr_pct', 'econ_pct'])

def belongs(r):
    """A level of an interaction with bowler type ('home|spin', or 'pace|left' for arm) belongs to that type only."""
    parts = r['level'].split('|')
    return len(parts) == 1 or r['bowler_type'] in parts

def estimate_effects():
    effects = level_effects(*fit_full())
    boot_eff = []
    for b in range(B_REFIT):
        counts = np.bincount(RNG.integers(0, len(match_list), len(match_list)), minlength=len(match_list))
        boot_eff.append(level_effects(*fit_full(counts[match_codes].astype(float)))['avg_pct'].to_numpy())
    effects['avg_lo'], effects['avg_hi'] = np.percentile(np.array(boot_eff), [2.5, 97.5], axis=0)
    effects = effects[effects.apply(belongs, axis=1)].copy()
    effects['level'] = effects['level'].str.replace(r'\|?(pace|spin)\|?', '', regex=True)
    return effects

# These effects come from the context model on all deliveries, so they don't depend on the wicket window.
# 200 refits take ~45 minutes, so they are cached; delete the file to recompute.
EFFECTS_CACHE = CACHE_DIR / f'level_effects_{B_REFIT}.csv'
if EFFECTS_CACHE.exists():
    effects = pd.read_csv(EFFECTS_CACHE, dtype={'level': str})
else:
    effects = estimate_effects()
    effects.to_csv(EFFECTS_CACHE, index=False)
print(f'{len(effects)} level effects, {B_REFIT} match-bootstrap refits')
effects[effects['variable'].isin(['home_x_type', 'lineup', 'partner'])].round(1)
