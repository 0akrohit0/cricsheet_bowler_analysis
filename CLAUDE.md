# Cricket Bowler Average Attribution

Research question: **which factors make one Test bowler's average lower than another's**, measured without restating
the definition of the average (average = SR × economy ÷ 6, so "takes wickets often" isn't an answer). Repo front page:
`README.md`. Remote: https://github.com/0akrohit0/cricsheet_bowler_analysis (branches `main` and `dev`; new work goes on `dev`).

## Working agreement

- **The report must be accurate, not consistent with earlier runs.** Headlines may change when the method or data
  improves, as long as the change has been audited from both a methodology and a code perspective (user, 14 Nov).
- Every number and claim in a report comes from `analysis/outputs/factor_results_100.json`.
  - Prose whose direction depends on the data (better/worse, which part is biggest, clear or not) is generated in
    `build_plain.py` / `report_app.js`.
  - The remaining fixed claims are asserted by `report/verify_claims.py`, which fails the run.
  - When a claim fails, reword it or make it data-driven. **Never loosen the check.**
- An effect is called "clear" only if its 95% interval excludes zero. Effects that aren't clear are either left out
  of the plain report's charts or described as "no clear difference".
- Edit `analysis/cells/` and `report/src/`, never the generated HTML.
- Paths are relative to the project folder. Don't hardcode absolute paths.

## Design rules (keep these)

1. **One window**: bowlers whose first Test is on or after **2007-01-01** and who reached **100 Test wickets**,
   measured over their first 100 (`WICKET_WINDOW = 100` in `01_setup.py`). The 50-wicket view was dropped on 14 Nov
   because it mixed in bowlers who didn't last.
2. **Strictly international**: `match_type == "Test"`, `team_type == "international"`, national sides only.
3. **Context is valued from everyone else.** Ball-level Poisson GLMs for wickets and runs (log link) are cross-fitted
   by bowler (5 folds). They use only what is known before the ball:
   - opposition line-up, batter vs line-up, set-ness, hand matchup;
   - ball age, innings, day, match state;
   - host country (from the event name, with a venue fallback; UAE counts as neutral), home/away;
   - era, DRS, umpire LBW rate;
   - role, spell, partner, type × arm.
4. **Bowler terms (added 14 Nov)**. `fit_glm` in `06_models.py` fits in two steps:
   1. conditions plus one indicator per bowler, so each condition is measured *within* bowlers;
   2. type × arm plus an intercept, with step 1's conditions as an offset (fit y/exp(o) with weight exp(o)). This
      gives the typical bowler of each type and arm.

   Type × arm is collinear with the bowler indicators, which is why it gets its own step. Scoring uses the condition
   coefficients plus the step-2 terms only.
5. **Attribution**:
   - xAvg = Σ expected runs ÷ Σ expected wickets;
   - exact grouped Shapley over 10 groups gives each group's contribution in runs per wicket;
   - bowler effect = actual − xAvg.
6. **Skill claims must survive out of sample**: a trait measured on wickets 1–50 has to predict wickets 51–100
   (split-half reliability and prediction, Spearman ρ, bootstrap CIs, BH q-values).
7. Mechanical stats (SR, economy, dots, maidens) are never explanatory features.
8. Level effects come from **200 match-bootstrap refits** (`B_REFIT` in `11_effects.py`), cached in
   `analysis/cache/level_effects_200.csv`.

Factor groups:
- **"Dealt"** (outside the bowler's control): Opposition line-up, Venue & home, Era & umpires, Match phase, Bowling
  partner, Bowling arm.
- **"Shaped"** (situations the bowler partly creates): Who's at the crease, Batter set or new, Match state, Role &
  usage.

## Data decisions

- Cricsheet `all_male_json` (data to Oct 2026): 898 Tests in total, of which 796 are in the model since 2007. That is
  1.53M deliveries by 692 bowlers.
- 19 of the 815 Tests since 2007 are missing from Cricsheet, mostly Afghanistan's. `02_parse.py` counts them from the
  ICC Test-number gaps, and the reports state the count.
- Batter histories start in 2001. The line-up strength uses the top seven who actually batted.
- Bowling type and arm come from `data/player_styles.csv`. Bowlers without a style are silently dropped in
  `05_design.py`, so run `update_styles.py` after every new download.

## Findings (Nov 2026 data, after the audit)

| | First 100 wickets (51 bowlers: 34 pace, 17 spin) |
|---|---|
| Spread in averages that is luck | 54% |
| Real spread: pace/spin · dealt · shaped · bowler | 16 · −4 · 2 · 86% |
| Run-control skill: reliability (2nd-half prediction) | 0.74 (0.46, q = 0.02) |
| Wicket-taking skill: reliability | 0.04 |
| Typical-conditions baseline | pace 30.6, spin 34.8 |

Effects on the average (% change, typical conditions):

| Condition | Effect |
|---|---|
| Weak line-up (28–31) / strong (46+) | −20.5 / +14.5% |
| Home / away | −5.3 / +5.7% (pace), −5.3 / +6.2% (spin) |
| Spin in Australia / Sri Lanka / India | +32 / −10 / −5% (India not clear) |
| Pace in West Indies | −13% |
| Spin, 4th innings | −14% |
| Spinner vs batter on the opposite side to his arm | −10% |
| Left-arm vs right-arm pace | −4.6 vs +1.0% |
| Partner | −1.5 to +3.3%, none clear |
| Era | at most 4.3% |

- The **dealt share is negative**: within these survivors, the bowlers dealt harder conditions were the better ones.
  Both reports explain this in a data-driven sentence. The plain report shows a negative share as "≈0%" and leaves it
  off the bar.
- GLM vs GBM log-loss: 0.0818 vs 0.0819. Calibration: −0.5% on wickets, +0.1% on runs.
- Spin-only variance shares are masked: real variance is ≈ 0 there (share real −0.02).
- Pre-debut profile and ODI record don't predict the second-half average (LOO R² −0.09).

## Audit (14 Nov): what changed and why

The sports-analyst and data-scientist review found that the context-only model credited **bowler composition** to
conditions. For example, India's spinners are good, so "spin in India" looked cheap. Adding bowler terms gave the
following changes against the Sep run (100-wicket column):

| Result | Before | After |
|---|---|---|
| Luck | 61% | 54% |
| Real spread: pace/spin · dealt · shaped · bowler | 19 · 26 · 9 · 46% | 16 · −4 · 2 · 86% |
| Partner effect | −6 / +8% | not clear |
| Spin in India | −11.5% | −4.7% (not clear) |
| Spin in Australia | +19% | +32% |
| Pace in Bangladesh, Zimbabwe | sign flips | |

- **Robust**: the line-up, home/away and era effects.
- **Other audit fixes**:
  - missing-Tests caveat;
  - 200 effect refits (was 60);
  - claim checks;
  - situational "skills" with *negative* reliability no longer listed as carrying over (an `abs()` bug);
  - arm and partner sentences made conditional on clear effects;
  - bowler names fall back to the registry's fullest alternative.
- **Open caveats**:
  - survivors only;
  - the within-bowler era effect also contains career stage;
  - bowler intervals leave out model uncertainty;
  - the halves are chronological, so form and learning sit inside reliability.

## Documents

- `report/Behind the Bowling Average.html/.pdf`: the plain-language report.
  - No correlations or intervals.
  - Results only in runs per wicket, % luck, or a 0–1 carry-over score.
- `report/Bowler Average Factors.html/.pdf`: the technical report.
  - `?print` draws every interactive view in the light theme for the PDF.
- The old claude.ai artifact (https://claude.ai/artifact/JvJjEhPh22pHn5zKFr58sQ) shows the **pre-audit** plain report
  and is stale. Republish it from `report/publish/` if it's needed again.

## Next steps

- Survivor check: rerun on all bowlers who reached 50 wickets (over their first 50) to see how much selection moves
  the dealt share. This needs `run_analysis.py 50` and the window-specific prose to be checked.
- Separate era from career stage (e.g. a Test-number term).

## Folder layout and how to rerun

```
data/                 all_male_json/ + zip (ignored), people.csv, names.csv, player_styles.csv, scrape_targets.csv
analysis/
  run_all.sh          download → update_styles → clear caches → analysis → verify_claims → report → report_plain → report_pdf
  cells/              01_setup … 14_export, run in one namespace by scripts/run_analysis.py [N]
  scripts/            download_data.py (won't overwrite without --force), update_styles.py, scrape_player_styles.py
  outputs/            factor_results_100.json
  logs/               <step>.log for each run_all step
  cache/              test_deliveries.pkl, white_ball_bowling.pkl, level_effects_200.csv (ignored; delete to rebuild)
report/               build_plain.py, build_report.py (→ also report/publish/, ignored), verify_claims.py, build_pdf.sh, src/
v1/                   the circular Sep–Oct 2026 analysis; on local disk only (ignored); in git history at commit dc60a0d
```

- Environment: conda env `data_work` (`/opt/miniconda3/envs/data_work`, Python 3.14, sklearn; no statsmodels or
  lightgbm). Run `PYTHON=python sh analysis/run_all.sh [--skip-download] [--skip-styles] [--keep-cache]`.
- A full run takes about an hour, of which `11_effects` (200 refits) is about 38 min. The GLMs use
  `solver='newton-cholesky'`, about 7 s per fit; lbfgs with bowler terms is slow and doesn't converge.
- New data invalidates every cache. `run_all.sh` clears them unless you pass `--keep-cache`.
- PDFs come from headless Chrome. To check pages without `pdftoppm`, render them with Swift PDFKit.

### Adding or changing a cell

- Cells share one namespace, in filename order. A final bare expression is printed to the log.
- Store new outputs in `14_export.py`'s JSON, and bind them in the report builders. Don't hardcode numbers in
  templates.
- After a change, run `verify_claims.py` and read both PDFs.

Bugs already fixed (don't reintroduce):
- **Venue → host**: use the event name ("X tour of Y", "X in Y Test Series") before falling back to the venue
  majority. Handle NaN events. UAE counts as neutral.
- **Shapley reference**: it must be interventional, type-matched and fold-consistent.
  - A mean-log-odds reference biased the baseline.
  - Fold-inconsistent intercepts made the arm effect vary within a type.
- **Log-link factorization**: use the exact form, E[exp(own_S + ref_¬S)] = exp(own_S)·E[exp(ref_¬S)], not Monte Carlo.
- **Hand matchup**: code it as same/opposite side × type. Coding it as hand × arm duplicated arm.
- **Type × arm with bowler terms**: fit it in step 2 of `fit_glm`. In one step it is collinear with the bowler
  indicators, and the arm coefficients come out arbitrary.
- **Bootstrap intervals**: assign them by `bowler_order` index (`put_interval`), with an assert lo ≤ est ≤ hi.
- **Effects filter**: it must keep the type levels (`belongs()`).
- **Situational reliability**: "carries over" means ρ ≥ 0.15, not |ρ| ≥ 0.15.
- **Negative variance shares**: show them as "≈0%" or explain them. Never print "−4%" as a share in the plain report.

## Conventions

- Reports use theme tokens with light and dark modes. Every chart bar is directly labelled. Pages are phone-width safe.
- Deliverable names are fixed: `Behind the Bowling Average.*`, `Bowler Average Factors.*`.

## Git

- `.gitignore` excludes the raw data, `analysis/cache/`, `v1/`, `report/publish/`, `__pycache__` and `.DS_Store`.
- Commit only code, reports (HTML and PDF), the results JSON, logs and the small registry/style CSVs. Notebooks are
  not used.
- Branches: commit new work on `dev`, which tracks `origin/dev`. It was created on 14 Nov at `33079cb`, the same commit
  as `main`. Merge into `main` only when the user asks.
- `gh` isn't installed and the GitHub MCP connector doesn't connect. Push over plain `git` to `origin`.
