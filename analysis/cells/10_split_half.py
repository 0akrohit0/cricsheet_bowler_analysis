def boot_spearman(x, y, n_boot=N_BOOT):
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho = stats.spearmanr(x, y)[0]
    idx = RNG.integers(0, len(x), size=(n_boot, len(x)))
    bs = np.array([stats.spearmanr(x[i], y[i])[0] for i in idx])
    return rho, *np.nanpercentile(bs, [2.5, 97.5])

def bh_qvalues(p):
    p = np.asarray(p); n = len(p); order = np.argsort(p)
    q = np.empty(n); q[order] = np.minimum.accumulate((p[order] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.minimum(q, 1)

# Context dealt in each half, from the same attribution machinery
def dealt_context(d):
    xr_, xw_, bm_ = attribute(d)
    c_, order_ = pd.factorize(bm_['bowler_id'])
    base_, xavg_, phi_, act_ = decompose(xr_, xw_, bm_, c_)
    out = pd.DataFrame(phi_, columns=GROUP_NAMES, index=order_)
    out['baseline'] = base_
    out['dealt'] = out[DEALT].sum(axis=1)
    return out

ctx_h1, ctx_h2 = dealt_context(win[win['half'] == 1]), dealt_context(win[win['half'] == 2])

# ---- reliability and prediction, one component at a time ---------------------------------------
# reliability: does the bowler show the same trait in both halves?
# predicts:    does the trait in the first half of the window predict how much better than context they are in the second?
#              (positive = more of the trait goes with doing better later)
rows = []
for comp in COMPONENTS:
    rel = boot_spearman(h1[comp], h2[comp])
    pred = boot_spearman(h1[comp], h2.loc[h1.index, 'overall skill'])
    p = stats.spearmanr(h1[comp], h2.loc[h1.index, 'overall skill'])[1]
    rows.append({'component': comp, 'reliability': rel[0], 'rel_lo': rel[1], 'rel_hi': rel[2],
                 'predicts 2nd-half skill': pred[0], 'pred_lo': pred[1], 'pred_hi': pred[2], 'p': p})
split = pd.DataFrame(rows).set_index('component')
split['q'] = bh_qvalues(split['p'])
# Also: does the raw first-half average predict the raw second-half average?
raw_rel = boot_spearman(h1['average'], h2.loc[h1.index, 'average'])
ctx_rel = boot_spearman(ctx_h1['dealt'], ctx_h2.loc[ctx_h1.index, 'dealt'])
print(f'Raw average, half 1 vs half 2: rho = {raw_rel[0]:.2f} [{raw_rel[1]:.2f}, {raw_rel[2]:.2f}]')
print(f'Dealt context, half 1 vs half 2: rho = {ctx_rel[0]:.2f} [{ctx_rel[1]:.2f}, {ctx_rel[2]:.2f}]')
split.round(2).sort_values('predicts 2nd-half skill')
