from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# 4D CHARTA ANALYZER
# FINAL HISTORY UPDATER V7.0
#
# HISTORY:
# 01-01-2020 -> TODAY
#
# MARKETS:
# - Magnum
# - Sports Toto
# - Da Ma Cai
# - Cash Sweep
#
# SOURCE:
# 4dmanager.net historical result pages
#
# STRATEGY:
# - Direct historical date pages
# - Do NOT depend on fragile page-date position
# - Parse operators independently
# - Preserve existing data
# - Preserve leading zeroes
# - Merge & deduplicate
# - FAIL if historical backfill does not really work
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

START_DATE = datetime(2020, 1, 1)
TODAY_DT = datetime.now()
TODAY = TODAY_DT.strftime("%Y-%m-%d")

BASE_URL = "https://4dmanager.net/result/{date}"

REQUEST_TIMEOUT = 25
REQUEST_DELAY = 0.15
MAX_RETRIES = 2


MARKETS = {

    "magnum": {
        "file": "magnum.json",
        "market": "Magnum 4D",
        "markers": [
            "Magnum 4D",
            "Magnum"
        ]
    },

    "toto": {
        "file": "toto.json",
        "market": "Sports Toto",
        "markers": [
            "TOTO 4D",
            "Sports Toto",
            "SportsToto",
            "Toto 4D"
        ]
    },

    "damacai": {
        "file": "damacai.json",
        "market": "Da Ma Cai",
        "markers": [
            "DaMaCai 1+3D",
            "Da Ma Cai",
            "DaMaCai"
        ]
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "market": "Cash Sweep",
        "markers": [
            "Cashsweep",
            "Cash Sweep",
            "Sarawak Cash Sweep"
        ]
    }
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
    "Connection": "keep-alive"
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value)
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

    if not isinstance(values, list):
        return output

    for value in values:

        number = normalize4(value)

        if (
            number
            and number not in output
        ):
            output.append(number)

    return output


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

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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


def load_database(path, market):

    default = {
        "market": market,
        "lastUpdated": "",
        "draws": []
    }

    data = load_json(
        path,
        default
    )

    if not isinstance(data, dict):
        data = default.copy()

    if not isinstance(
        data.get("draws"),
        list
    ):
        data["draws"] = []

    data["market"] = market

    return data


# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(value):

    if not value:
        return None

    value = clean_text(value)

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d-%b-%Y"
    ):

        try:
            return datetime.strptime(
                value,
                fmt
            )

        except ValueError:
            pass

    return None


def iso_date(value):

    dt = parse_date(value)

    if not dt:
        return ""

    return dt.strftime(
        "%Y-%m-%d"
    )


# ============================================================
# HTML -> CLEAN LINES
# ============================================================

def html_to_lines(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for bad in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
        bad.decompose()

    text = soup.get_text(
        "\n",
        strip=True
    )

    lines = []

    for raw in text.splitlines():

        line = clean_text(raw)

        if line:
            lines.append(line)

    return lines


# ============================================================
# PAGE VALIDATION
#
# V5 ERROR:
# only searched first 80 lines.
#
# V7:
# searches entire page for requested date.
# ============================================================

def page_contains_date(
    lines,
    requested_date
):

    requested_dt = parse_date(
        requested_date
    )

    if not requested_dt:
        return False

    formats = {
        requested_dt.strftime("%d/%m/%Y"),
        requested_dt.strftime("%Y-%m-%d"),
        requested_dt.strftime("%d-%m-%Y"),
        requested_dt.strftime("%d %b %Y"),
        requested_dt.strftime("%d-%b-%Y")
    }

    full_text = "\n".join(
        lines
    )

    return any(
        date_text in full_text
        for date_text in formats
    )


# ============================================================
# FIND MARKET START
# ============================================================

def find_market_start(
    lines,
    markers
):

    for i, line in enumerate(lines):

        low = line.lower()

        for marker in markers:

            marker_low = (
                marker.lower()
            )

            if marker_low in low:

                # Avoid top navigation line:
                # Magnum · Toto · DaMaCai ...
                operator_count = sum(
                    word in low
                    for word in [
                        "magnum",
                        "toto",
                        "damacai",
                        "cashsweep"
                    ]
                )

                if operator_count >= 3:
                    continue

                return i

    return None


# ============================================================
# MARKET BLOCK
# ============================================================

def extract_market_block(
    lines,
    market_key
):

    cfg = MARKETS[
        market_key
    ]

    start = find_market_start(
        lines,
        cfg["markers"]
    )

    if start is None:
        return []


    other_markers = []

    for other_key, other_cfg in (
        MARKETS.items()
    ):

        if other_key == market_key:
            continue

        other_markers.extend(
            other_cfg["markers"]
        )


    end = len(lines)


    for i in range(
        start + 1,
        len(lines)
    ):

        low = lines[i].lower()

        matched_other = False

        for marker in other_markers:

            if marker.lower() in low:

                operator_count = sum(
                    word in low
                    for word in [
                        "magnum",
                        "toto",
                        "damacai",
                        "cashsweep"
                    ]
                )

                if operator_count < 3:

                    matched_other = True
                    break


        if matched_other:

            end = i
            break


    return lines[
        start:end
    ]


# ============================================================
# FOUR-DIGIT EXTRACTION
#
# Handles:
#
# 928638509898...
#
# by splitting:
#
# 9286 3850 9898 ...
# ============================================================

def extract_4d_numbers(text):

    output = []

    groups = re.findall(
        r"\d+",
        str(text)
    )

    for group in groups:

        if len(group) == 4:

            output.append(
                group
            )

        elif (
            len(group) > 4
            and len(group) % 4 == 0
        ):

            for i in range(
                0,
                len(group),
                4
            ):

                chunk = group[
                    i:i + 4
                ]

                if len(chunk) == 4:
                    output.append(
                        chunk
                    )

    return output


# ============================================================
# SINGLE PRIZE
# ============================================================

def find_single_prize(
    block,
    prize_names
):

    for i, line in enumerate(
        block
    ):

        low = line.lower()

        if not any(
            name in low
            for name in prize_names
        ):
            continue


        # Same line
        nums = extract_4d_numbers(
            line
        )

        if nums:
            return nums[-1]


        # Next few lines
        for j in range(
            i + 1,
            min(
                i + 5,
                len(block)
            )
        ):

            nums = (
                extract_4d_numbers(
                    block[j]
                )
            )

            if nums:
                return nums[0]


    return ""


# ============================================================
# PRIZE LIST
# ============================================================

def find_prize_list(
    block,
    start_words,
    stop_words
):

    start = None

    for i, line in enumerate(
        block
    ):

        low = line.lower()

        if any(
            word in low
            for word in start_words
        ):

            start = i + 1
            break


    if start is None:
        return []


    numbers = []


    for i in range(
        start,
        len(block)
    ):

        low = block[
            i
        ].lower()


        if any(
            word in low
            for word in stop_words
        ):
            break


        found = extract_4d_numbers(
            block[i]
        )


        for number in found:

            if number not in numbers:

                numbers.append(
                    number
                )


            if len(numbers) >= 10:

                return numbers[:10]


    return numbers[:10]


# ============================================================
# PARSE ONE MARKET
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


    # Ensure this market block itself
    # belongs to requested date.
    if not page_contains_date(
        block,
        requested_date
    ):
        return None


    first = find_single_prize(
        block,
        [
            "1st prize",
            "1st",
            "头奖"
        ]
    )


    second = find_single_prize(
        block,
        [
            "2nd prize",
            "2nd",
            "二奖"
        ]
    )


    third = find_single_prize(
        block,
        [
            "3rd prize",
            "3rd",
            "三奖"
        ]
    )


    if not (
        first
        and second
        and third
    ):
        return None


    special = find_prize_list(
        block,
        [
            "special",
            "特别奖"
        ],
        [
            "consolation",
            "安慰奖"
        ]
    )


    consolation = find_prize_list(
        block,
        [
            "consolation",
            "安慰奖"
        ],
        [
            "jackpot",
            "next draw",
            "more result",
            "past result"
        ]
    )


    return {
        "draw": "",
        "date": requested_date,
        "first": normalize4(first),
        "second": normalize4(second),
        "third": normalize4(third),
        "special": normalize_list(
            special
        ),
        "consolation": normalize_list(
            consolation
        )
    }


# ============================================================
# RECORD QUALITY
# ============================================================

def record_score(record):

    score = 0

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

    if record.get("draw"):
        score += 2

    return score


# ============================================================
# MERGE
# ============================================================

def merge_record(
    database,
    new_record
):

    new_date = new_record[
        "date"
    ]


    for i, old in enumerate(
        database["draws"]
    ):

        old_date = iso_date(
            old.get(
                "date"
            )
        )


        if old_date != new_date:
            continue


        # Preserve existing draw number
        if (
            not new_record.get(
                "draw"
            )
            and old.get(
                "draw"
            )
        ):

            new_record[
                "draw"
            ] = str(
                old["draw"]
            )


        if (
            record_score(
                new_record
            )
            >
            record_score(
                old
            )
        ):

            database[
                "draws"
            ][i] = new_record

            return True


        return False


    database[
        "draws"
    ].append(
        new_record
    )

    return True


# ============================================================
# CLEAN DATABASE
# ============================================================

def clean_database(database):

    unique = {}


    for old in database[
        "draws"
    ]:

        if not isinstance(
            old,
            dict
        ):
            continue


        date_value = iso_date(
            old.get(
                "date"
            )
        )


        if (
            not date_value
            or date_value < "2020-01-01"
            or date_value > TODAY
        ):
            continue


        record = {

            "draw": str(
                old.get(
                    "draw",
                    ""
                )
            ),

            "date":
                date_value,

            "first":
                normalize4(
                    old.get(
                        "first"
                    )
                ),

            "second":
                normalize4(
                    old.get(
                        "second"
                    )
                ),

            "third":
                normalize4(
                    old.get(
                        "third"
                    )
                ),

            "special":
                normalize_list(
                    old.get(
                        "special",
                        []
                    )
                ),

            "consolation":
                normalize_list(
                    old.get(
                        "consolation",
                        []
                    )
                )
        }


        if not (
            record["first"]
            and record["second"]
            and record["third"]
        ):

            continue


        key = date_value


        if key not in unique:

            unique[key] = record

        elif (
            record_score(record)
            >
            record_score(
                unique[key]
            )
        ):

            unique[key] = record


    draws = list(
        unique.values()
    )


    draws.sort(
        key=lambda x:
            x["date"],
        reverse=True
    )


    database[
        "draws"
    ] = draws


    if draws:

        newest = draws[0][
            "date"
        ]

        oldest = draws[-1][
            "date"
        ]

    else:

        newest = ""
        oldest = ""


    database[
        "lastUpdated"
    ] = newest


    database[
        "historyCoverage"
    ] = {

        "drawCount":
            len(draws),

        "oldestDate":
            oldest,

        "newestDate":
            newest
    }


    database[
        "historyRange"
    ] = {

        "from":
            "2020-01-01",

        "to":
            TODAY
    }


    database[
        "historySource"
    ] = (
        "4dmanager.net historical archive"
    )


# ============================================================
# HTTP
# ============================================================

def fetch_page(
    session,
    date_value
):

    url = BASE_URL.format(
        date=date_value
    )


    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )


            if response.status_code == 404:

                return None


            response.raise_for_status()


            if len(
                response.text
            ) < 500:

                return None


            return response.text


        except Exception as error:

            if (
                attempt
                ==
                MAX_RETRIES
            ):

                print(
                    "  HTTP ERROR:",
                    error
                )

                return None


            time.sleep(
                attempt
            )


    return None


# ============================================================
# DATE SELECTION
#
# Main MY 4D historical draw days:
#
# Tuesday
# Wednesday
# Saturday
# Sunday
#
# Includes special draws.
# ============================================================

def should_scan(dt):

    return dt.weekday() in {
        1,  # Tue
        2,  # Wed
        5,  # Sat
        6   # Sun
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 66)
    print("4D CHARTA ANALYZER")
    print("FINAL HISTORY UPDATER V7")
    print("2020 -> CURRENT")
    print("=" * 66)


    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    databases = {}


    for key, cfg in (
        MARKETS.items()
    ):

        databases[
            key
        ] = load_database(

            DATA_DIR
            / cfg["file"],

            cfg["market"]
        )


    session = requests.Session()


    requested_pages = 0
    valid_pages = 0
    parsed_records = 0
    changed_records = 0


    # Counts specifically before 2026,
    # so we know REAL backfill happened.
    historical_records = {
        key: 0
        for key in MARKETS
    }


    cursor = TODAY_DT


    while cursor >= START_DATE:

        if not should_scan(
            cursor
        ):

            cursor -= timedelta(
                days=1
            )

            continue


        date_value = (
            cursor.strftime(
                "%Y-%m-%d"
            )
        )


        requested_pages += 1


        if (
            requested_pages % 50
            == 0
        ):

            print()
            print(
                "Progress:",
                requested_pages,
                "pages"
            )


        html = fetch_page(
            session,
            date_value
        )


        if not html:

            cursor -= timedelta(
                days=1
            )

            continue


        lines = html_to_lines(
            html
        )


        # Page must contain requested date
        # somewhere in entire document.
        if not page_contains_date(
            lines,
            date_value
        ):

            cursor -= timedelta(
                days=1
            )

            time.sleep(
                REQUEST_DELAY
            )

            continue


        records_this_page = 0


        for key in MARKETS:

            record = parse_market(
                lines,
                key,
                date_value
            )


            if not record:
                continue


            records_this_page += 1
            parsed_records += 1


            if date_value < "2026-01-01":

                historical_records[
                    key
                ] += 1


            changed = merge_record(
                databases[key],
                record
            )


            if changed:

                changed_records += 1


            print(
                "✓",
                date_value,
                key.upper(),
                record["first"],
                record["second"],
                record["third"],
                "S:",
                len(
                    record[
                        "special"
                    ]
                ),
                "C:",
                len(
                    record[
                        "consolation"
                    ]
                )
            )


        if records_this_page:

            valid_pages += 1


        time.sleep(
            REQUEST_DELAY
        )


        cursor -= timedelta(
            days=1
        )


    # ========================================================
    # SAVE / VALIDATE
    # ========================================================

    print()
    print("=" * 66)
    print("DATABASE RESULT")
    print("=" * 66)


    failures = []


    for key, cfg in (
        MARKETS.items()
    ):

        database = databases[
            key
        ]


        clean_database(
            database
        )


        coverage = database[
            "historyCoverage"
        ]


        print()
        print(
            cfg["market"]
        )

        print(
            " Draw count :",
            coverage[
                "drawCount"
            ]
        )

        print(
            " Oldest     :",
            coverage[
                "oldestDate"
            ]
        )

        print(
            " Newest     :",
            coverage[
                "newestDate"
            ]
        )

        print(
            " Pre-2026 parsed:",
            historical_records[
                key
            ]
        )


        # Save only after parsing
        save_json(
            DATA_DIR
            / cfg["file"],
            database
        )


        # ================================================
        # REAL VALIDATION
        #
        # We don't want another fake green run.
        # ================================================

        if (
            coverage[
                "drawCount"
            ]
            < 30
        ):

            failures.append(
                f"{key}: "
                f"only "
                f"{coverage['drawCount']} draws"
            )


        oldest = coverage[
            "oldestDate"
        ]


        if (
            not oldest
            or oldest > "2021-12-31"
        ):

            failures.append(
                f"{key}: "
                f"oldest={oldest or 'NONE'}"
            )


    print()
    print("=" * 66)
    print("FINAL SUMMARY")
    print("=" * 66)

    print(
        "Pages requested:",
        requested_pages
    )

    print(
        "Valid pages:",
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


    if failures:

        print()
        print(
            "BACKFILL VALIDATION FAILED"
        )

        for failure in failures:

            print(
                " -",
                failure
            )


        raise RuntimeError(
            "Historical database "
            "did not pass validation."
        )


    print()
    print(
        "V7 HISTORY BACKFILL SUCCESS ✓"
    )

    print(
        "Database now contains "
        "real historical results "
        "from 2020 onward."
    )

    print("=" * 66)


if __name__ == "__main__":
    main()
