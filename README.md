# What makes a Test bowling average low?

This repo asks which factors make one Test bowler's average lower than another's, without restating what the average is.
"They take wickets often and don't concede many runs" is just runs ÷ wickets in other words, so it doesn't count as an
answer.

The analysis prices every delivery in international Tests since 2007 using every other bowler. It then splits each
bowler's average into:

- the conditions they were dealt;
- the situations they partly created;
- what is left, which is the bowler.

Finally it checks which of the bowler's traits repeat out of sample.

The study group is the **51 bowlers who debuted in 2007 or later and reached 100 Test wickets**, measured over their first
100 wickets. The data is Cricsheet ball-by-ball, covering 898 international Tests up to Oct 2026.

## Reports

- **[`report/Behind the Bowling Average.pdf`](report/Behind%20the%20Bowling%20Average.pdf)**: a plain-language report
  for non-technical readers (10 pages).
- **[`report/Bowler Average Factors.pdf`](report/Bowler%20Average%20Factors.pdf)**: the technical report, with methods,
  every chart, the bowler table and the caveats (17 pages).

The `.html` versions next to them are interactive (theme toggle, any bowler's breakdown, every condition).

## Answers in brief

| Question | Answer (first 100 wickets, 51 bowlers) |
|---|---|
| How much of the spread in averages is luck? | **54%.** Sampling noise accounts for over half the variance. A bowler's average over wickets 1–50 barely predicts wickets 51–100 (ρ = 0.19). |
| Of the real spread, what matters? | **The bowler: 86%.** Pace vs spin accounts for 16% and match situations for 2%. Conditions dealt to the bowler come out at **−4%**: they move every delivery's price, but over 100 wickets they mostly even out, and the bowlers dealt harder conditions tended to be the better ones. |
| Which skill repeats? | **Run control.** Conceding fewer runs than the conditions predict carries over between halves (ρ = 0.74) and predicts beating the conditions later (ρ = 0.46, q = 0.02). Taking more wickets than predicted doesn't repeat (ρ = 0.04), even though it drives most of the visible spread. |
| Biggest single conditions | **Opposition line-up**: weak (top seven averaging 28–31) −20%, strong (46+) +15%. **Home vs away**: about 11%. **Spinners by country**: Australia +32%, Sri Lanka −10%. **Fourth innings for spinners**: −14%. **Batter on the opposite side to a spinner's arm**: −10%. **Left-arm pace**: about 6% cheaper than right-arm. |
| What doesn't matter | The bowling partner (no clear effect once bowler identity is controlled), umpires' LBW tendencies, era (at most 4%), and pre-debut profile (type, age, ODI record), which predicts none of the later average (LOO R² < 0). |

All percentages are changes in a typical bowler's average with everything else held at typical values. Intervals come
from 200 match-bootstrap refits and are in the technical report.

## Repository layout

```
data/
  all_male_json/                      Cricsheet ball-by-ball JSON (not in git; download_data.py fetches it)
  people.csv, names.csv               Cricsheet player registry
  player_styles.csv                   bowling type and arm per player (scraped from Cricinfo; update_styles.py tops it up)
analysis/
  run_all.sh                          full rerun: download → styles → analysis → claim checks → reports → PDFs (~1 h)
  requirements.txt                    library versions the results were built with (Python 3.14)
  cells/01_setup.py … 14_export.py    the analysis, in order (parse → features → windows → design → models →
                                      Shapley → bootstrap → skill → split-half → effects → prediction → sensitivity → export)
  scripts/run_analysis.py             runs the cells in one namespace and writes the results JSON
  scripts/download_data.py            fetches the latest Cricsheet archive
  scripts/update_styles.py            refreshes the registry and scrapes styles for new Test players
  scripts/scrape_player_styles.py     the style scraper
  outputs/factor_results_100.json     every number the reports use
  logs/                               printed output of each step (cache/ holds rebuildable caches, not in git)
report/
  Behind the Bowling Average.html/.pdf  plain-language report
  Bowler Average Factors.html/.pdf      technical report
  build_plain.py, build_report.py     fill the templates in src/ from the results JSON
  verify_claims.py                    checks every fixed claim in the reports against the JSON; fails the run if one breaks
  build_pdf.sh                        prints both reports to PDF with headless Chrome
  src/                                templates, chart and app JS
CLAUDE.md                             design rules, decisions, audit notes and gotchas for the AI assistant
```

## Reproduce

```sh
pip install -r analysis/requirements.txt
sh analysis/run_all.sh                                        # latest data, full rebuild (~1 h, needs network)
sh analysis/run_all.sh --skip-download --skip-styles --keep-cache   # rebuild from what's on disk
```

- PDFs need Google Chrome. Set `CHROME=/path/to/chrome` if it isn't in `/Applications`.
- Newer Cricsheet data will shift the numbers. The reports' prose is generated from the JSON, and `verify_claims.py`
  stops the run if a fixed claim no longer holds.

## Key definitions and data notes

**Scope**
- International men's Tests (`team_type == international`), national sides only.
- A bowler's window must start on or after 2007-01-01. Ball-level batter histories start in 2001, so their records are
  established by then.

**Expected average (xAvg)**
- Cross-fitted Poisson GLMs for wickets and runs per ball (5 folds by bowler), fitted on everything known before the ball:
  - opposition line-up, the batter's record, set-ness and hand;
  - ball age, innings, day and match state;
  - host country and home/away, era, DRS, umpire;
  - spell, role, partner, and bowling type × arm.
- The models include a term for each bowler, so a condition is measured *within* bowlers and doesn't take credit for who
  usually bowls there.
- xAvg = Σ expected runs ÷ Σ expected wickets for a typical bowler.
- The additive GLM matches a gradient-boosting benchmark on log-loss (0.0818 vs 0.0819).

**Attribution**
- Exact grouped Shapley values over 10 factor groups, in runs per wicket.
- **Dealt** (outside the bowler's control): line-up, venue and home, era and umpires, match phase, partner, arm.
- **Shaped** (partly the bowler's doing): who's at the crease, batter set or new, match state, role and usage.
- Bowler effect = actual − xAvg.

**Luck**
- Each bowler's Tests are resampled with replacement. The variance that resampling produces is subtracted from the
  observed spread.

**Skill**
- Context-adjusted log ratios.
- Reliability compares wickets 1–50 with 51–100 (Spearman ρ, bootstrap CI). Prediction asks whether a first-half trait
  predicts beating the conditions in the second half. P-values are BH-corrected (q).
- Mechanical stats (strike rate, economy, dots, maidens) are never used as explanations.

**Caveats**
- Survivors only: bowlers who were dropped before 100 wickets aren't in the sample.
- 19 of the 815 Tests since 2007 are missing from Cricsheet (mostly Afghanistan's).
- The line-up measure counts only batters who batted.
- Bowler intervals leave out model uncertainty.
- The era effect within a bowler also contains career stage.
