from itertools import combinations
from math import factorial

# "Typical Test conditions" for a group means the group takes the context of a random league delivery
# bowled by the same type of bowler (pace or spin), so a spinner is compared with typical spin conditions.
# Both models have a log link and are additive across groups, so that expectation factors out exactly:
#     E[exp(own_S + ref_notS)] = exp(own_S) * E_league,type[exp(ref_notS)]
# The league expectation uses the same fold model as the bowler's own deliveries: each group's indicators
# are collinear with the intercept, so the constant is split differently in every fold.
# Pace vs spin itself is not a Shapley group; it shows up as a different baseline for each type.
G = len(GROUP_NAMES)
COALITIONS = [frozenset(c) for r in range(G + 1) for c in combinations(range(G), r)]
COAL_INDEX = {c: i for i, c in enumerate(COALITIONS)}
MASK = np.array([[g in S for g in range(G)] for S in COALITIONS], dtype=float)    # (n_coalitions, G)
CHUNK = 50_000
TYPES = ['pace', 'spin']
type_code = ctx['bowler_type'].map({t: i for i, t in enumerate(TYPES)}).to_numpy()

def group_eta(model):
    """Linear predictor of every league delivery split by group, under one fold's model. Shape (n, G)."""
    return np.column_stack([X_ctx[:, col_group == g] @ model.coef_[col_group == g] for g in GROUP_NAMES])

def league_factor(eta):
    """E over deliveries of exp(sum of the groups NOT in each coalition). Shape (n_coalitions,)."""
    total = np.zeros(len(COALITIONS))
    for a in range(0, len(eta), CHUNK):
        total += np.exp(eta[a:a + CHUNK] @ (1 - MASK).T).sum(0)
    return total / len(eta)

def league_factors(model):
    eta = group_eta(model)
    return np.stack([league_factor(eta[type_code == ti]) for ti in range(len(TYPES))])

C_WKT = np.stack([league_factors(pw) for pw, _ in glm_models])    # (n_folds, n_types, n_coalitions)
C_RUN = np.stack([league_factors(pr) for _, pr in glm_models])

def coalition_sums(rows, keys):
    """Expected runs and wickets summed by key for every coalition of groups. Shape (n_coalitions, n_keys).

    Each key must belong to a single bowler, so all its deliveries share a fold and a bowler type.
    """
    codes, uniq = pd.factorize(keys)
    xr = np.zeros((len(COALITIONS), len(uniq))); xw = np.zeros_like(xr)
    for a in range(0, len(rows), CHUNK):
        r, c = rows[a:a + CHUNK], codes[a:a + CHUNK]
        A = sparse.csr_matrix((np.ones(len(r)), (c, np.arange(len(r)))), shape=(len(uniq), len(r)))
        cw, cr = C_WKT[fold[r], type_code[r]], C_RUN[fold[r], type_code[r]]
        xw += (A @ (np.exp(icpt_wkt[r, None] + eta_wkt[r] @ MASK.T) * cw)).T
        xr += (A @ (np.exp(icpt_run[r, None] + eta_run[r] @ MASK.T) * cr)).T
    return xr, xw, uniq

def shapley(value):
    """Grouped Shapley values from value[coalition_index, unit]. Returns (n_units, n_groups)."""
    phi = np.zeros((value.shape[1], G))
    for gi in range(G):
        for S in COALITIONS:
            if gi in S: continue
            wgt = factorial(len(S)) * factorial(G - len(S) - 1) / factorial(G)
            phi[:, gi] += wgt * (value[COAL_INDEX[S | {gi}]] - value[COAL_INDEX[S]])
    return phi

def attribute(w):
    """Per-bowler decomposition: actual average = typical-conditions baseline + sum of context factors + bowler."""
    pos = ctx.reset_index().set_index('seq').loc[w['seq'], 'index'].to_numpy()
    # Sums by (bowler, match) so we can bootstrap over matches cheaply afterwards
    key = w['bowler_id'].to_numpy() + '|' + w['match_id'].astype(str).to_numpy()
    xr, xw, uniq = coalition_sums(pos, key)
    bm = pd.DataFrame({'key': uniq})
    bm[['bowler_id', 'match_id']] = bm['key'].str.split('|', expand=True)
    act = w.assign(key=key).groupby('key').agg(runs=('bowler_runs', 'sum'), wkts=('is_wicket', 'sum'))
    bm = bm.join(act, on='key')
    return xr, xw, bm

def decompose(xr, xw, bm, codes=None):
    """Aggregate (bowler, match) sums to bowlers and return the decomposition table."""
    if codes is None:
        codes, _ = pd.factorize(bm['bowler_id'])
    n = codes.max() + 1
    R = np.stack([np.bincount(codes, r, minlength=n) for r in xr])
    W = np.stack([np.bincount(codes, x, minlength=n) for x in xw])
    value = R / W                                  # expected average under each coalition
    phi = shapley(value)
    actual = np.bincount(codes, bm['runs'], minlength=n) / np.bincount(codes, bm['wkts'], minlength=n)
    return value[COAL_INDEX[frozenset()]], value[-1], phi, actual

xr, xw, bm = attribute(win)
codes, bowler_order = pd.factorize(bm['bowler_id'])
baseline, xavg, phi, actual = decompose(xr, xw, bm, codes)

att = pd.DataFrame(phi, columns=GROUP_NAMES, index=bowler_order)
att['baseline'] = baseline
att['xAvg'] = xavg
att['actual'] = actual
att['bowler_effect'] = att['actual'] - att['xAvg']           # what context can't explain
att['skill_ratio'] = att['actual'] / att['xAvg']
att = bowlers[['bowler', 'team', 'bowler_type']].join(att)
assert np.allclose(att[GROUP_NAMES].sum(axis=1), att['xAvg'] - att['baseline'])
assert np.allclose(att['actual'], bowlers.loc[att.index, 'average'])

print('Typical-conditions baseline by type (runs/wkt):', att.groupby('bowler_type')['baseline'].agg(['mean', 'std']).round(2).to_dict('index'))
print(f"Spread of averages across bowlers (sd): actual {att['actual'].std():.2f}, context-expected {att['xAvg'].std():.2f}, "
      f"bowler effect {att['bowler_effect'].std():.2f}")
att['dealt'] = att[DEALT].sum(axis=1)
att['shaped'] = att[SHAPED].sum(axis=1)
print(f"League runs per wicket {LEAGUE_AVG:.2f}")
print(f"Spearman(actual, xAvg) = {stats.spearmanr(att['actual'], att['xAvg'])[0]:.2f}")
PARTS = GROUP_NAMES + ['dealt', 'shaped', 'bowler_effect']
spread = pd.DataFrame({'sd across bowlers': att[PARTS].std(), 'mean |effect|': att[PARTS].abs().mean(),
                       'corr with actual avg': att[PARTS].corrwith(att['actual'], method='spearman')})
spread.sort_values('sd across bowlers', ascending=False).round(2)
