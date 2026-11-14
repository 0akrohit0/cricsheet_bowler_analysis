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

## Rerun on the latest data
```
pip install -r requirements.txt
python run_all.py
```
This takes about 75 minutes and needs network access. It:
1. downloads the latest [`all_male_json.zip`](https://cricsheet.org/downloads/all_male_json.zip) from Cricsheet
   (about 130 MB) into `all_male_json/`;
2. refreshes the Cricsheet registry (`people.csv`, `names.csv`) and scrapes Cricinfo for the bowling style of any
   new Test player (`player_styles.csv`, which ships with the repo);
3. clears `cache/`, executes both notebooks, and rebuilds the three HTML reports listed above.

Each report shows the date range of the data it was built from. Cricsheet adds matches as they are played, so
results move a little from run to run.

Options: `--skip-download` reuses the data already on disk, `--skip-styles` skips the registry and scraping, and
`--keep-cache` reuses `cache/` (only when the data hasn't changed). The individual steps live in `pipeline/`
(`download_data.py`, `update_styles.py`, `build_notebook.py N`, `build_report.py N`, `plain/build_plain.py`).
Edit the cells in `pipeline/nb/`, not the `.ipynb` files; the notebooks are generated.
