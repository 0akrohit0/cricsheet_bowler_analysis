#!/bin/sh
# Rerun the whole analysis on the latest Cricsheet data and rebuild the reports and PDFs (about an hour, needs network).
# Usage, from the project folder: sh analysis/run_all.sh [--skip-download] [--skip-styles] [--keep-cache]
#   --skip-download  reuse data/all_male_json        --skip-styles  don't refresh the registry or scrape styles
#   --keep-cache     reuse analysis/cache (only if the data hasn't changed)
set -e
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
DOWNLOAD=1; STYLES=1; CLEAR=1
for a in "$@"; do
  case "$a" in
    --skip-download) DOWNLOAD=0 ;; --skip-styles) STYLES=0 ;; --keep-cache) CLEAR=0 ;;
    *) echo "unknown option: $a"; exit 2 ;;
  esac
done
mkdir -p analysis/logs analysis/outputs
# run <log name> <command...>: output goes to analysis/logs/<log name>.log; on failure show its tail and stop
run() { log="analysis/logs/$1.log"; shift; echo "== $log ($(date +%H:%M))"
        "$@" > "$log" 2>&1 || { tail -40 "$log"; exit 1; }; }

[ $DOWNLOAD = 1 ] && run download_data  $PY analysis/scripts/download_data.py --force
[ $STYLES = 1 ]   && run update_styles  $PY analysis/scripts/update_styles.py
[ $CLEAR = 1 ]    && rm -f analysis/cache/test_deliveries.pkl analysis/cache/white_ball_bowling.pkl analysis/cache/level_effects_*.csv
run analysis       $PY analysis/scripts/run_analysis.py
run verify_claims  $PY report/verify_claims.py
run report         $PY report/build_report.py
run report_plain   $PY report/build_plain.py
run report_pdf     sh report/build_pdf.sh
echo "done: results in analysis/outputs, reports in report/, printed output in analysis/logs"
