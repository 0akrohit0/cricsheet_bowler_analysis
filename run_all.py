"""Rerun the whole analysis on the latest Cricsheet data and write the HTML reports.

  1. download the latest all_male_json.zip into all_male_json/
  2. refresh the Cricsheet registry and scrape bowling styles for new Test players
  3. clear the caches built from the old data
  4. execute the 50- and 100-wicket notebooks (about 35 minutes each)
  5. build the two technical reports and the plain-language report

Usage: python run_all.py [--skip-download] [--skip-styles] [--keep-cache]
"""
import argparse, subprocess, sys, time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
PIPELINE = PROJECT / 'pipeline'
CACHES = ['test_deliveries.pkl', 'white_ball_bowling.pkl', 'level_effects_*.csv']
OUTPUTS = ['Behind the Bowling Average.html',
           'Bowler Average Factors - First 50.html', 'Bowler Average Factors - First 100.html']

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--skip-download', action='store_true', help='reuse the data already in all_male_json/')
ap.add_argument('--skip-styles', action='store_true', help="don't refresh the registry or scrape new styles")
ap.add_argument('--keep-cache', action='store_true', help="reuse cache/ (only safe if the data hasn't changed)")
args = ap.parse_args()

def step(title, *cmd):
    print(f'\n=== {title}', flush=True)
    t0 = time.time()
    subprocess.run([sys.executable, *map(str, cmd)], cwd=PROJECT, check=True)
    print(f'=== {title}: done in {(time.time() - t0) / 60:.1f} min', flush=True)

if not args.skip_download:
    step('Download Cricsheet data', PIPELINE / 'download_data.py', '--force')
if not args.skip_styles:
    step('Bowling styles for new players', PIPELINE / 'update_styles.py')
if not args.keep_cache:
    for pattern in CACHES:
        for f in (PROJECT / 'cache').glob(pattern):
            f.unlink()
            print('removed cache/' + f.name)
for n in (50, 100):
    step(f'Notebook: first {n} wickets', PIPELINE / 'build_notebook.py', n)
for n in (50, 100):
    step(f'Report: first {n} wickets', PIPELINE / 'build_report.py', n)
step('Plain-language report', PIPELINE / 'plain' / 'build_plain.py')

print('\nReports:')
for name in OUTPUTS:
    print(' ', PROJECT / name)
