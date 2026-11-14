# Cricket Bowler Average Attribution

Research question: **which factors make one Test bowler's average lower than another's**, measured without
restating the definition of the average.

## History

- **v1 (Sep–Oct 2026)**: `Cricket Bowler Average Attribution.ipynb` and `Test Bowler Average Analysis.ipynb`, reported in
  `Low Test Bowling Averages.html` (data: `report_results.json`). It was judged **circular**: average = SR × econ ÷ 6,
  "removes batters before they're set" just restates runs per wicket, and the workload and team-win effects
  probably run in reverse. Kept for reference only; don't build on it.
- **v2 (Nov 2026)**: a non-circular redesign (below). This is the current analysis.

## v2 design rules (keep these)

1. **Level playing field**: each bowler's **first N Test wickets** (N = 50 main, 100 second run). The window must start
   on or after **2007-01-01** (left-censoring cutoff).
2. **Strictly international**: `match_type == "Test"`, `team_type == "international"`, national sides only
   (893 Tests).
3. **Context is valued from everyone else.** Ball-level Poisson GLMs for wickets and runs are cross-fitted by bowler
   (5 folds). They use only what is known before the ball: opposition line-up, batter vs line-up, set-ness, ball age,
   innings, match state, host country (taken from the event name, with a venue fallback; UAE counts as neutral),
   home/away, era, DRS, umpire, role, spell, partner, and type × arm.
   - xAvg = Σ expected runs ÷ Σ expected wickets.
   - Exact grouped Shapley over 10 factor groups gives each group's contribution in runs per wicket.
4. **Skill claims must survive out of sample**: a trait measured on wickets 1…N/2 has to predict wickets
   N/2+1…N (split-half reliability and prediction, BH q-values).
5. Mechanical stats (SR, economy, dots, maidens) are never explanatory features.

Factor groups:
- **"Dealt"** (outside the bowler's control): Opposition line-up, Venue & home, Era & umpires, Match phase,
  Bowling partner, Bowling arm.
- **"Shaped"** (situations the bowler partly creates): Who's at the crease, Batter set or new, Match state,
  Role & usage.

## Key results

| | First 50 wickets | First 100 wickets |
|---|---|---|
| Bowlers | 109 | 49 |
| Spread in averages that is luck (sampling noise) | 64% | 61% |
| Real spread: pace/spin · dealt · shaped · bowler | 16 · 40 · 24 · 20% | 19 · 26 · 9 · 46% |
| Run-control skill: reliability (2nd-half prediction) | 0.54 (0.28, q≈0.08) | 0.64 (0.23, CI includes 0) |
| Wicket-taking skill: reliability | 0.17 | −0.04 |

Effects on the average:

| Condition | Effect |
|---|---|
| Weak opposition line-up | −21% |
| Strong opposition line-up | +14.5% |
| Home | −5% |
| Away | +6% |
| Good bowling partner | −6% |
| Poor bowling partner | +8% |
| Spin in India | −11% |
| Spin in Australia | +19% |

Other notes:
- The GLM matches a GBM benchmark on log-loss (0.0817 vs 0.0819), so the additive model is adequate.
- Pre-debut ODI/T20I records don't predict reliably; the ODI link doesn't replicate between windows.

## Open questions / next steps

- **Survivor confound**: the 49 bowlers in the 100-wicket group are the ones good enough to last. To separate
  window length from selection, rerun the first-50 analysis on just those 49 bowlers. This hasn't been run yet.
- The technical reports haven't been published as artifacts; only the beginner report has been.

## Files

**Deliverables (project root)**
- `Bowler Average Factors - First 50.ipynb` / `.html` with `factor_results.json`: the 50-wicket run.
- `Bowler Average Factors - First 100.ipynb` / `.html` with `factor_results_100.json`: the 100-wicket run.
- `Behind the Bowling Average.html`: the plain-language report combining both runs, for non-technical readers.
  It is also published privately at https://claude.ai/artifact/JvJjEhPh22pHn5zKFr58sQ.

**Data**
- `all_male_json/`: Cricsheet ball-by-ball JSON, 18,259 matches (Sep 2026 snapshot). `all_male_json.zip` is the
  original archive. `pipeline/download_data.py` fetches the latest archive, which is newer and larger; it won't
  overwrite existing data without `--force`.
- `people.csv`, `names.csv`: Cricsheet registry.
- `player_styles.csv`: bowling type and arm. Run `scrape_player_styles.py` with targets in `scrape_targets.csv`;
  it needs network access.
- `cache/`:
  - `test_deliveries.pkl`: parsed Tests.
  - `white_ball_bowling.pkl`: ODI/T20I.
  - `level_effects_60.csv`: 60 bootstrap refits; slow to regenerate.
  - Delete a cache file to force a rebuild.
- The other CSVs (`First 100 Wickets…`, `Test First 100 Wickets.csv`, `test_*.csv`, …) are v1 intermediates, read
  only by the v1 notebooks.

**Pipeline (`pipeline/`)**: the source of truth. The notebooks are generated from it, so edit here, not in the
`.ipynb`.
- `nb/01_setup.py` … `nb/15_export.py`: notebook cells, in order:
  setup → parse → ball features → windows → design matrix → models → Shapley attribution → match bootstrap →
  skill components → split-half → level effects → prediction / white-ball → 50 vs 100 sensitivity → figures →
  JSON export.
- `build_notebook.py N`: assembles the cells, sets the window constants, executes the notebook in a fresh kernel,
  and writes the `.ipynb` and the results JSON.
- `build_report.py N`: fills `report_template.html` with `report_charts.js` and `report_app.js` and the JSON, and
  writes the technical HTML. Prose is data-driven, so the 100 report doesn't claim 50-only findings. A
  no-wrapper copy goes to `pipeline/publish/` for artifact publishing.
- `plain/build_plain.py`: builds the beginner report from both JSONs using `plain/template.html`. Every number
  comes from the JSONs; the build asserts that no `{{placeholder}}` remains.
- `kexec.py`: sends a .py file to a running Jupyter kernel, for interactive debugging. Copy that kernel's
  connection file to `pipeline/kernel.json` first.
- Paths are relative to the repo (`PROJECT = dirname(HERE)`). Don't hardcode absolute paths.

**Rebuild everything** (use the `data_work` conda env, `/opt/miniconda3/envs/data_work`, which has sklearn but not
statsmodels or lightgbm):
```
conda activate data_work
python pipeline/build_notebook.py 50 && python pipeline/build_notebook.py 100
python pipeline/build_report.py 50 && python pipeline/build_report.py 100
python pipeline/plain/build_plain.py
```

## Bugs already fixed: don't reintroduce

- Venue → host: use the event name ("X tour of Y", "X in Y Test Series") before falling back to the venue majority.
  Handle NaN events. UAE counts as neutral.
- The Shapley reference must be **interventional, type-matched and fold-consistent**:
  - a mean-log-odds reference biased the baseline (35.0 vs league 32.35);
  - fold-inconsistent intercepts made the arm effect vary within a type.
- Use the exact log-link factorization, E[exp(own_S + ref_¬S)] = exp(own_S)·E[exp(ref_¬S)], not Monte Carlo.
- The hand-matchup feature is coded as same/opposite side × type. Coded as hand × arm, it duplicated arm.
- Bootstrap intervals are assigned by `bowler_order` index (`put_interval`), with an assert lo ≤ est ≤ hi. Row
  order once misaligned.
- The effects filter must keep type levels (`belongs()`).
- Deliverable names are always `Bowler Average Factors - First N.*`. `build_report.py` writes the cross-links
  from that pattern, so don't rename outputs by hand.
- Spin-only variance shares are unstable (real variance ≈ 0). They are masked as NaN when the real share is
  < 0.15, and shown as "≈0%".

## Conventions

- Reports: theme tokens with light and dark modes, every chart bar directly labelled, phone-width safe.
- Beginner report: no correlations or intervals; results only in runs per wicket, % luck, or a 0–1 carry-over
  score.
- Leave the v1 files untouched.

## Git

- `.gitignore` excludes the raw data (`all_male_json/`, the zip), `cache/`, the v1 CSVs (some are over 100 MB) and
  `pipeline/publish/`. Commit only code, reports, results JSONs and the small registry/style CSVs.
- `gh` isn't installed. Push over plain `git` to the remote that's already configured.
