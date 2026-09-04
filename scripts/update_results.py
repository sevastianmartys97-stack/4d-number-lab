from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# 4D CHARTA ANALYZER
# FINAL LIGHTWEIGHT AUTO UPDATER
#
# IMPORTANT:
# - DOES NOT rebuild history.
# - DOES NOT scan 2021-2026.
# - Only checks recent dates.
# - Keeps the large historical databases intact.
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

BASE_URL = "https://4d-my.com/4d-past-results/?draw={date}"

# Check only recent days.
# Enough to catch delayed/missed GitHub Actions runs.
LOOKBACK_DAYS = 7

REQUEST_TIMEOUT = 30


MARKETS = {

    "magnum": {
        "file": "magnum.json",
        "market": "Magnum 4D",
        "markers": [
            "Magnum 4D",
            "Magnum"
        ],
    },

    "damacai": {
        "file": "damacai.json",
        "market": "Da Ma Cai",
        "markers": [
            "Da Ma Cai 1+3D",
            "Da Ma Cai",
            "DaMaCai"
        ],
    },

    "toto": {
        "file": "toto.json",
        "market": "Sports Toto",
        "markers": [
            "SportsToto 4D",
            "Sports Toto",
            "SportsToto"
        ],
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "market": "Cash Sweep",
        "markers": [
            "Sarawak Cash Sweep",
            "Cash Sweep",
            "CashSweep"
        ],
    },
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def normalize4(value):

    if value is None:
        return ""

    digits = re.sub(
        r"\D",
        "",
        str(value)
    )

    if not digits:
        return ""

    return digits[-4:].zfill(4)


def normalize_list(values):

    output = []

    for value in values or []:

        number = normalize4(value)

        if number and number not in output:
            output.append(number)

    return output


def normalize_date(value):

    value = clean_text(value)

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d-%b-%Y",
    ):

        try:

            dt = datetime.strptime(
                value,
                fmt
            )

            return dt.strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            pass

    return ""


# ============================================================
# JSON
# ============================================================

def load_json(path, default):

    try:

        with path.open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return default


def save_json(path, data):

    with path.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

        f.write("\n")


# ============================================================
# PAGE TEXT
# ============================================================

def html_to_lines(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        tag.decompose()

    text = soup.get_text(
        "\n",
        strip=True
    )

    return [
        clean_text(line)
        for line in text.splitlines()
        if clean_text(line)
    ]


# ============================================================
# MARKET BLOCK
# ============================================================

def find_market_start(
    lines,
    markers
):

    for i, line in enumerate(lines):

        low = line.lower()

        for marker in markers:

            if marker.lower() in low:
                return i

    return None


def extract_market_block(
    lines,
    market_key
):

    config = MARKETS[
        market_key
    ]

    start = find_market_start(
        lines,
        config["markers"]
    )

    if start is None:
        return []


    other_markers = []

    for other_key, other_config in MARKETS.items():

        if other_key == market_key:
            continue

        other_markers.extend(
            other_config["markers"]
        )


    end = len(lines)

    for i in range(
        start + 1,
        len(lines)
    ):

        low = lines[i].lower()

        if any(
            marker.lower() in low
            for marker in other_markers
        ):

            end = i
            break


    return lines[
        start:end
    ]


# ============================================================
# FIND DRAW HEADER
# ============================================================

def parse_draw_header(
    block,
    requested_date
):

    full_text = " ".join(
        block[:15]
    )


    # Examples:
    # #417/26(Wed) 02-Sep-2026
    # #5339(Wed) 02-Sep-2026

    match = re.search(
        r"#\s*([0-9]+(?:/[0-9]+)?)"
        r".{0,30}?"
        r"(\d{2}-[A-Za-z]{3}-\d{4})",
        full_text
    )


    if match:

        draw = match.group(1)

        date_value = normalize_date(
            match.group(2)
        )

        if date_value != requested_date:
            return "", ""

        return draw, date_value


    # If draw number pattern failed,
    # still verify date exists.

    requested_dt = datetime.strptime(
        requested_date,
        "%Y-%m-%d"
    )

    date_text = requested_dt.strftime(
        "%d-%b-%Y"
    )


    if date_text.lower() not in full_text.lower():
        return "", ""

    return "", requested_date


# ============================================================
# PRIZE HELPERS
# ============================================================

def extract_4d_numbers(text):

    return re.findall(
        r"(?<!\d)\d{4}(?!\d)",
        str(text)
    )


def find_single_prize(
    block,
    names
):

    for i, line in enumerate(block):

        low = line.lower()

        if not any(
            name in low
            for name in names
        ):
            continue


        numbers = extract_4d_numbers(
            line
        )

        if numbers:
            return numbers[-1]


        for j in range(
            i + 1,
            min(i + 4, len(block))
        ):

            numbers = extract_4d_numbers(
                block[j]
            )

            if numbers:
                return numbers[0]


    return ""


def find_prize_list(
    block,
    start_word,
    stop_word=None
):

    start = None


    for i, line in enumerate(block):

        if start_word.lower() in line.lower():

            start = i + 1
            break


    if start is None:
        return []


    numbers = []


    for i in range(
        start,
        len(block)
    ):

        line = block[i]

        if (
            stop_word
            and stop_word.lower()
            in line.lower()
        ):
            break


        found = extract_4d_numbers(
            line
        )


        for number in found:

            number = normalize4(
                number
            )

            if number not in numbers:
                numbers.append(number)


            if len(numbers) >= 10:
                return numbers[:10]


    return numbers[:10]


# ============================================================
# PARSE MARKET
# ============================================================

def parse_market(
    lines,
    market_key,
    requested_date
):

    block = extract_market_block(
        lines,
        market_key
    )


    if not block:
        return None


    draw, date_value = parse_draw_header(
        block,
        requested_date
    )


    if not date_value:
        return None


    first = find_single_prize(
        block,
        [
            "1st prize",
            "1st"
        ]
    )


    second = find_single_prize(
        block,
        [
            "2nd prize",
            "2nd"
        ]
    )


    third = find_single_prize(
        block,
        [
            "3rd prize",
            "3rd"
        ]
    )


    special = find_prize_list(
        block,
        "Special",
        "Consolation"
    )


    consolation = find_prize_list(
        block,
        "Consolation"
    )


    if not (
        first
        and second
        and third
    ):
        return None


    if len(special) < 10:
        return None


    if len(consolation) < 10:
        return None


    return {

        "draw":
            draw,

        "date":
            date_value,

        "first":
            normalize4(first),

        "second":
            normalize4(second),

        "third":
            normalize4(third),

        "special":
            normalize_list(
                special
            )[:10],

        "consolation":
            normalize_list(
                consolation
            )[:10],
    }


# ============================================================
# RECORD QUALITY
# ============================================================

def record_score(record):

    score = 0

    if record.get("draw"):
        score += 2

    for field in (
        "first",
        "second",
        "third"
    ):

        if record.get(field):
            score += 10

    score += len(
        record.get(
            "special",
            []
        )
    )

    score += len(
        record.get(
            "consolation",
            []
        )
    )

    return score


# ============================================================
# MERGE WITHOUT DESTROYING HISTORY
# ============================================================

def merge_record(
    database,
    new_record
):

    date_value = new_record[
        "date"
    ]


    for index, old in enumerate(
        database.get(
            "draws",
            []
        )
    ):

        old_date = normalize_date(
            old.get(
                "date"
            )
        )


        if old_date != date_value:
            continue


        if (
            not new_record.get("draw")
            and old.get("draw")
        ):

            new_record[
                "draw"
            ] = str(
                old["draw"]
            )


        if (
            record_score(new_record)
            >
            record_score(old)
        ):

            database[
                "draws"
            ][index] = new_record

            return True


        return False


    database.setdefault(
        "draws",
        []
    ).append(
        new_record
    )


    return True


# ============================================================
# UPDATE METADATA
# ============================================================

def update_metadata(
    database,
    market_name
):

    valid = []


    for record in database.get(
        "draws",
        []
    ):

        if not isinstance(
            record,
            dict
        ):
            continue


        date_value = normalize_date(
            record.get("date")
        )


        if not date_value:
            continue


        record["date"] = date_value

        valid.append(record)


    valid.sort(
        key=lambda x:
            x["date"],
        reverse=True
    )


    database[
        "draws"
    ] = valid


    if valid:

        newest = valid[0][
            "date"
        ]

        oldest = valid[-1][
            "date"
        ]

    else:

        newest = ""
        oldest = ""


    database[
        "market"
    ] = market_name


    database[
        "lastUpdated"
    ] = newest


    database[
        "historyCoverage"
    ] = {

        "drawCount":
            len(valid),

        "oldestDate":
            oldest,

        "newestDate":
            newest
    }


    # IMPORTANT:
    # Keep the actual historical
    # coverage already built.

    database[
        "historyRange"
    ] = {

        "from":
            "2021-01-01",

        "to":
            datetime.now().strftime(
                "%Y-%m-%d"
            )
    }


# ============================================================
# FETCH DATE
# ============================================================

def fetch_date(
    session,
    date_value
):

    url = BASE_URL.format(
        date=date_value
    )


    try:

        response = session.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )


        if response.status_code == 404:
            return None


        response.raise_for_status()


        if len(response.text) < 1000:
            return None


        return response.text


    except Exception as error:

        print(
            "HTTP ERROR",
            date_value,
            error
        )

        return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "4D CHARTA ANALYZER"
    )

    print(
        "FINAL LIGHTWEIGHT UPDATER"
    )

    print("=" * 70)


    databases = {}


    for key, config in MARKETS.items():

        path = (
            DATA_DIR
            / config["file"]
        )


        database = load_json(
            path,
            {
                "market":
                    config["market"],

                "draws":
                    []
            }
        )


        if not isinstance(
            database.get("draws"),
            list
        ):

            database[
                "draws"
            ] = []


        databases[
            key
        ] = database


    session = requests.Session()


    today = datetime.now()


    pages_checked = 0
    valid_pages = 0
    parsed_records = 0
    changed_records = 0


    for days_back in range(
        LOOKBACK_DAYS
    ):

        dt = today - timedelta(
            days=days_back
        )


        date_value = dt.strftime(
            "%Y-%m-%d"
        )


        print()
        print(
            "Checking:",
            date_value
        )


        pages_checked += 1


        html = fetch_date(
            session,
            date_value
        )


        if not html:

            print(
                "  No result page."
            )

            continue


        lines = html_to_lines(
            html
        )


        page_hits = 0


        for key, config in MARKETS.items():

            record = parse_market(
                lines,
                key,
                date_value
            )


            if not record:
                continue


            parsed_records += 1
            page_hits += 1


            changed = merge_record(
                databases[key],
                record
            )


            if changed:

                changed_records += 1

                print(
                    "  +",
                    config["market"],
                    record["draw"],
                    record["first"],
                    record["second"],
                    record["third"]
                )

            else:

                print(
                    "  =",
                    config["market"],
                    "already exists"
                )


        if page_hits:

            valid_pages += 1


    # ========================================================
    # SAVE
    # ========================================================

    print()
    print("=" * 70)
    print("DATABASE STATUS")
    print("=" * 70)


    for key, config in MARKETS.items():

        database = databases[
            key
        ]


        update_metadata(
            database,
            config["market"]
        )


        path = (
            DATA_DIR
            / config["file"]
        )


        save_json(
            path,
            database
        )


        coverage = database[
            "historyCoverage"
        ]


        print()

        print(
            config["market"]
        )

        print(
            " Draws :",
            coverage[
                "drawCount"
            ]
        )

        print(
            " Oldest:",
            coverage[
                "oldestDate"
            ]
        )

        print(
            " Newest:",
            coverage[
                "newestDate"
            ]
        )


    # ========================================================
    # META
    # ========================================================

    meta = {

        "lastRun":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "lookbackDays":
            LOOKBACK_DAYS,

        "pagesChecked":
            pages_checked,

        "validPages":
            valid_pages,

        "recordsParsed":
            parsed_records,

        "recordsChanged":
            changed_records,

        "mode":
            "lightweight-recent-results-only"
    }


    save_json(
        DATA_DIR
        / "update_meta.json",
        meta
    )


    print()
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(
        "Pages checked :",
        pages_checked
    )

    print(
        "Valid pages   :",
        valid_pages
    )

    print(
        "Records parsed:",
        parsed_records
    )

    print(
        "New / changed:",
        changed_records
    )

    print()
    print(
        "Historical database preserved."
    )

    print(
        "No 2021-2026 backfill was run."
    )

    print()
    print(
        "FINAL LIGHTWEIGHT UPDATE COMPLETE ✓"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
