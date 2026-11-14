#!/bin/sh
# Print the two HTML reports to PDF with headless Chrome. The ?print flag makes the technical reports draw
# every interactive view (all conditions, both skill charts) in the light theme; page size is set in the CSS.
# Usage, from the project folder: sh report/build_pdf.sh   (set CHROME to use another Chrome/Chromium binary)
set -e
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
for name in "Behind the Bowling Average" "Bowler Average Factors"; do
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --window-size=720,1000 --virtual-time-budget=15000 \
    --print-to-pdf="$PWD/$name.pdf" "file://$PWD/$name.html?print" 2>/dev/null
  echo "wrote report/$name.pdf"
done
