"""Fill the report template with factor_results.json and the chart code.
Writes the project's standalone HTML file and a publish-ready copy (no document wrapper) in the scratchpad."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
RESULTS = 'factor_results.json' if N == 50 else f'factor_results_{N}.json'
NAME = f'Bowler Average Factors - First {N}'
page = open(os.path.join(HERE, 'report_template.html')).read()
if N != 50:
    page = page.replace('<title>Bowler Average Factors</title>', f'<title>Bowler Factors at {N} Wickets</title>')
data = json.load(open(os.path.join(PROJECT, RESULTS)))
# Local cross-link between the two windows (only in the project copy; a published page has no sibling file)
other = 100 if N == 50 else 50
other_file = f'Bowler Average Factors - First {other}.html'
companion = f' · <a href="{other_file}">same analysis over the first {other} wickets</a>'
page = (page.replace('/*__DATA__*/null', json.dumps(data, separators=(',', ':')).replace('</', '<\\/'))
            .replace('/*__CHARTS__*/', open(os.path.join(HERE, 'report_charts.js')).read())
            .replace('/*__APP__*/', open(os.path.join(HERE, 'report_app.js')).read()))

with open(os.path.join(HERE, 'publish', f'{NAME}.html'), 'w') as f:
    f.write(page.replace('<!--__COMPANION__-->', ''))
page = page.replace('<!--__COMPANION__-->', companion)
standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + page.replace('<div class="page">', '</head>\n<body>\n<div class="page">', 1) + '\n</body>\n</html>\n')
with open(os.path.join(PROJECT, f'{NAME}.html'), 'w') as f:
    f.write(standalone)
print('report written,', len(standalone) // 1024, 'KB')
