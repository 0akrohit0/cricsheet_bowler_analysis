"""Fill the technical report template with analysis/outputs/factor_results_<N>.json and the chart code.
Writes report/Bowler Average Factors.html and a publish-ready copy (no document wrapper) in report/publish/.
Usage, from the project folder: python report/build_report.py [N]   (default 100)"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
NAME = 'Bowler Average Factors'
data = json.load(open(os.path.join(PROJECT, 'analysis', 'outputs', f'factor_results_{N}.json')))
src = lambda f: open(os.path.join(HERE, 'src', f)).read()
page = (src('report_template.html')
        .replace('/*__DATA__*/null', json.dumps(data, separators=(',', ':')).replace('</', '<\\/'))
        .replace('/*__CHARTS__*/', src('report_charts.js'))
        .replace('/*__APP__*/', src('report_app.js')))

os.makedirs(os.path.join(HERE, 'publish'), exist_ok=True)
with open(os.path.join(HERE, 'publish', f'{NAME}.html'), 'w') as f:
    f.write(page)
standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + page.replace('<div class="page">', '</head>\n<body>\n<div class="page">', 1) + '\n</body>\n</html>\n')
with open(os.path.join(HERE, f'{NAME}.html'), 'w') as f:
    f.write(standalone)
print('report written,', len(standalone) // 1024, 'KB')
