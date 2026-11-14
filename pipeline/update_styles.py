"""Top up player_styles.csv for Test players it doesn't cover yet (new debutants after a data refresh).
Refreshes Cricsheet's people/names registry, finds Test players with no row in player_styles.csv, and scrapes
only those from Cricinfo. Players already tried (including permanent failures) are never re-fetched.
Usage: python pipeline/update_styles.py [--no-registry]"""
import csv, json, os, subprocess, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
REGISTRY = {'people.csv': 'https://cricsheet.org/register/people.csv',
            'names.csv': 'https://cricsheet.org/register/names.csv'}
TARGETS = PROJECT / 'cache' / 'style_targets.csv'

if '--no-registry' not in sys.argv:
    for name, url in REGISTRY.items():
        print('Refreshing', name, flush=True)
        urllib.request.urlretrieve(url, PROJECT / name)

# Every player listed in a Test (the notebook narrows this to national sides later)
test_players = {}
for path in sorted((PROJECT / 'all_male_json').glob('*.json')):
    text = path.read_text()
    if '"match_type": "Test"' not in text:      # cheap pre-filter before parsing
        continue
    info = json.loads(text)['info']
    registry = info.get('registry', {}).get('people', {})
    for names in info.get('players', {}).values():
        for name in names:
            if name in registry:
                test_players[registry[name]] = name

with open(PROJECT / 'player_styles.csv', newline='', encoding='utf-8') as f:
    tried = {row['identifier'] for row in csv.DictReader(f)}
with open(PROJECT / 'people.csv', newline='', encoding='utf-8') as f:
    cricinfo = {row['identifier']: row['key_cricinfo'] for row in csv.DictReader(f)}

new = sorted(set(test_players) - tried)
targets = [{'player_id': i, 'identifier': i, 'key_cricinfo': cricinfo.get(i, ''), 'unique_name': test_players[i]}
           for i in new]
no_key = [t['unique_name'] for t in targets if not t['key_cricinfo']]
print(f'{len(test_players)} Test players, {len(new)} without a style row'
      + (f' ({len(no_key)} have no Cricinfo id and are skipped: {", ".join(no_key)})' if no_key else ''), flush=True)
if not [t for t in targets if t['key_cricinfo']]:
    sys.exit(0)

TARGETS.parent.mkdir(exist_ok=True)
with open(TARGETS, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['player_id', 'identifier', 'key_cricinfo', 'unique_name'])
    w.writeheader()
    w.writerows(targets)
subprocess.run([sys.executable, 'scrape_player_styles.py', str(TARGETS)], cwd=PROJECT, check=True)
