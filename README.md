# Cricket Bowler Average Attribution

Which factors make one Test bowler's average lower than another's, measured without restating the definition of
the average? Each bowler is compared over their **first 50 (and first 100) Test wickets** since 2007, with the
context they bowled in (opposition, venue, era, partner, match phase, …) valued from every other bowler via
cross-fitted ball-level Poisson GLMs and an exact grouped Shapley attribution.

## Reports
- `Behind the Bowling Average.html`: plain-language summary of both runs.
- `Bowler Average Factors - First 50.html` / `- First 100.html`: technical reports.
- `Bowler Average Factors - First 50.ipynb` / `- First 100.ipynb`: the executed notebooks.
- `Low Test Bowling Averages.html` and the other two notebooks are the earlier (v1) analysis, kept for reference.

## Data
Raw ball-by-ball data is not in the repo. Fetch it from Cricsheet (about 130 MB) with:
```
python pipeline/download_data.py
```
This unzips [`all_male_json.zip`](https://cricsheet.org/downloads/all_male_json.zip) into `all_male_json/`.
Cricsheet updates that archive as new matches are played, so a fresh download includes more matches than the
one behind the published results (18,259 matches, downloaded September 2026), and the numbers will shift a little.
`people.csv`, `names.csv` and `player_styles.csv` (bowling type and arm) are included.

## Rebuild
Requires Python with pandas, numpy, scipy, scikit-learn, matplotlib, seaborn, jupyter_client and ipykernel.
```
python pipeline/build_notebook.py 50 && python pipeline/build_notebook.py 100   # ~35 min each; caches to cache/
python pipeline/build_report.py 50 && python pipeline/build_report.py 100
python pipeline/plain/build_plain.py
```
Edit the cells in `pipeline/nb/`, not the `.ipynb` files; the notebooks are generated.
