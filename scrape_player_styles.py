"""
Scrapes batting hand / bowling style / date of birth for a list of players
from ESPNCricinfo, using the key_cricinfo IDs found in Cricsheet's people.csv.

Source page used: stats.espncricinfo.com/ci/engine/player/{id}.html
This is the older Statsguru "player" page, not the modern cricketers/ page.
It's server-rendered plain HTML with a single consistent summary line, e.g.:

    Matthew Hoggard - right-hand bat; right-arm fast-medium

...directly above a "Player profile" link. That makes it much easier to
scrape reliably than the modern React-based profile pages, which render
most content client-side.

INPUT
    A CSV with at least these columns: identifier, key_cricinfo, unique_name
    (this is exactly what scrape_targets.csv from the earlier filtering step
    looks like).

OUTPUT
    player_styles.csv with columns:
    identifier, unique_name, key_cricinfo, batting_style, bowling_style,
    date_of_birth, scrape_status

RESUMABILITY
    Re-running the script skips any identifier already present (with a
    successful status) in the output file, so it's safe to stop and restart.
"""

import time
import random
import re
import csv
import os
import sys

import requests
from bs4 import BeautifulSoup

# ---- config -----------------------------------------------------------

INPUT_CSV = sys.argv[1] if len(sys.argv) > 1 else "scrape_targets.csv"
OUTPUT_CSV = "player_styles.csv"

MIN_DELAY_SECONDS = 1.5   # politeness delay between requests
MAX_DELAY_SECONDS = 3.0
REQUEST_TIMEOUT = 15
MAX_RETRIES_PER_PLAYER = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

URL_TEMPLATE = "https://stats.espncricinfo.com/ci/engine/player/{key}.html?class=1;type=allround"

OUTPUT_FIELDS = [
    "identifier", "unique_name", "key_cricinfo",
    "batting_style", "bowling_style", "date_of_birth", "scrape_status",
]

# ---- parsing ------------------------------------------------------------

def parse_style_line(html_text):
    """
    Given the raw HTML of a stats.espncricinfo.com player page, extract
    (batting_style, bowling_style, date_of_birth).

    Anchors on stable, known TEXT PATTERNS ("...-hand bat", "Player profile",
    "Born <date>") rather than on line position. Line-position matching
    (e.g. "whatever line comes right before 'Player profile'") turned out to
    be fragile in practice: BeautifulSoup's get_text() doesn't necessarily
    break lines in the same places a browser or a readability-style content
    extractor would, so the "previous line" trick was sometimes grabbing the
    wrong text without ever raising an error -- it always found *a* line, just
    not always the *right* one, so failures were silent instead of loud.
    Anchoring on the actual wording is robust to that regardless of how the
    surrounding HTML happens to be nested or wrapped.

    Raises ValueError if the page doesn't look like a player page at all
    (e.g. it's a redirect/error page and none of the expected anchors
    appear anywhere on it).
    """
    soup = BeautifulSoup(html_text, "html.parser")
    # Collapse all whitespace (including newlines from nested tags) to single
    # spaces, so matching doesn't depend on where line breaks happen to fall.
    text = " ".join(soup.get_text(" ").split())

    profile_match = re.search(r"player profile", text, re.IGNORECASE)
    if not profile_match:
        raise ValueError("Could not find the 'Player profile' anchor on this page")

    # Look at a window of text just before that anchor, and within it find
    # the batting-style phrase -- this phrase's wording is far more stable
    # than trying to guess where a "line" starts.
    window_start = max(0, profile_match.start() - 200)
    window = text[window_start:profile_match.start()]

    style_match = re.search(r"(?:right|left)-hand\s*bat.*$", window, re.IGNORECASE)
    if not style_match:
        raise ValueError(
            "Found 'Player profile' anchor but no batting-style phrase before it "
            "-- page layout may have changed"
        )

    styles_chunk = style_match.group(0).rstrip("- ").strip()
    pieces = [p.strip() for p in styles_chunk.split(";") if p.strip()]
    batting_style = pieces[0] if len(pieces) >= 1 else None
    bowling_style = pieces[1] if len(pieces) >= 2 else None

    # "Born December 31, 1976" -- searched across the whole normalized text
    dob_match = re.search(r"\bBorn\s+([A-Z][a-z]+ \d{1,2},\s*\d{4})", text)
    date_of_birth = dob_match.group(1) if dob_match else None

    return batting_style, bowling_style, date_of_birth


# ---- fetching -----------------------------------------------------------

def fetch_player_page(session, key_cricinfo):
    url = URL_TEMPLATE.format(key=int(key_cricinfo))
    response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def scrape_one_player(session, key_cricinfo):
    """
    Returns (batting_style, bowling_style, date_of_birth, status_string).
    status_string is "ok", or a short description of what went wrong.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES_PER_PLAYER + 1):
        try:
            html_text = fetch_player_page(session, key_cricinfo)
            batting_style, bowling_style, dob = parse_style_line(html_text)
            return batting_style, bowling_style, dob, "ok"
        except requests.exceptions.RequestException as e:
            last_error = f"request_error: {e}"
        except ValueError as e:
            last_error = f"parse_error: {e}"

        if attempt < MAX_RETRIES_PER_PLAYER:
            time.sleep(random.uniform(2, 4))  # back off a bit more before retrying

    return None, None, None, last_error or "unknown_error"


# ---- main -----------------------------------------------------------

def load_already_done(output_path):
    done = set()
    if os.path.exists(output_path):
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("scrape_status") == "ok":
                    done.add(row["identifier"])
    return done


def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Input file not found: {INPUT_CSV}")
        sys.exit(1)

    with open(INPUT_CSV, "r", newline="", encoding="utf-8") as f:
        targets = list(csv.DictReader(f))

    already_done = load_already_done(OUTPUT_CSV)
    remaining = [t for t in targets if t["identifier"] not in already_done
                 and t.get("key_cricinfo")]

    print(f"Total targets: {len(targets)}")
    print(f"Already scraped successfully: {len(already_done)}")
    print(f"Remaining to fetch: {len(remaining)}")

    write_header = not os.path.exists(OUTPUT_CSV)
    session = requests.Session()

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        if write_header:
            writer.writeheader()

        for i, target in enumerate(remaining, start=1):
            key_cricinfo = target["key_cricinfo"]
            identifier = target["identifier"]
            unique_name = target.get("unique_name", "")

            batting_style, bowling_style, dob, status = scrape_one_player(
                session, key_cricinfo
            )

            writer.writerow({
                "identifier": identifier,
                "unique_name": unique_name,
                "key_cricinfo": key_cricinfo,
                "batting_style": batting_style,
                "bowling_style": bowling_style,
                "date_of_birth": dob,
                "scrape_status": status,
            })
            f.flush()  # write progress to disk immediately, don't lose it on interrupt

            marker = "OK" if status == "ok" else f"FAILED ({status})"
            print(f"[{i}/{len(remaining)}] {unique_name} ({key_cricinfo}): {marker}")

            time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    print(f"\nDone. Results in {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
