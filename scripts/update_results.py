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
# HISTORY DATABASE V5.0
#
# RANGE:
#   01-01-2020 → TODAY
#
# MARKETS:
#   Magnum
#   Sports Toto
#   Da Ma Cai
#   Cash Sweep
#
# SOURCE:
#   4dmanager.net historical result pages
#
# IMPORTANT:
# - Preserve existing JSON
# - Merge historical data
# - Exact date validation
# - Preserve leading zero
# - Skip non-draw dates
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

START_DATE = datetime(2020, 1, 1)
TODAY = datetime.now()

BASE_URL = "https://4dmanager.net/result/{date}"

REQUEST_DELAY = 0.18
REQUEST_TIMEOUT = 25


MARKETS = {
    "magnum": {
        "file": "magnum.json",
        "market": "Magnum 4D",
        "aliases": [
            "magnum 4d",
            "magnum"
        ]
    },

    "toto": {
        "file": "toto.json",
        "market": "Sports Toto",
        "aliases": [
            "toto 4d",
            "sports toto",
            "toto"
        ]
    },

    "damacai": {
        "file": "damacai.json",
        "market": "Da Ma Cai",
        "aliases": [
            "damacai 1+3d",
            "da ma cai",
            "damacai"
        ]
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "market": "Cash Sweep",
        "aliases": [
            "cashsweep",
            "cash sweep",
            "sarawak cash sweep"
        ]
    }
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_number(value):
    digits = re.sub(r"\D", "", str(value))

    if not digits:
        return ""

    return digits[-4:].zfill(4)


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
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def iso_date(value):
    dt = parse_date(value)

    if not dt:
        return ""

    return dt.strftime("%Y-%m-%d")


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    except Exception:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(
            data,
            fh,
            ensure_ascii=False,
            indent=2
        )

        fh.write("\n")


def load_database(path, market):
    default = {
        "market": market,
        "lastUpdated": "",
        "historyRange": {
            "from": "2020-01-01",
            "to": ""
        },
        "draws": []
    }

    data = load_json(path, default)

    if not isinstance(data, dict):
        data = default

    if not isinstance(data.get("draws"), list):
        data["draws"] = []

    data["market"] = market

    return data


# ============================================================
# NUMBER EXTRACTION
#
# 4dmanager sometimes gives:
#
# 928638509898...
#
# instead of:
#
# 9286 3850 9898...
#
# This function splits long digit groups into 4 digits.
# ============================================================

def extract_4d_numbers(text):
    results = []

    digit_groups = re.findall(r"\d+", str(text))

    for group in digit_groups:

        if len(group) == 4:
            results.append(group)

        elif len(group) > 4 and len(group) % 4 == 0:

            for i in range(0, len(group), 4):
                chunk = group[i:i + 4]

                if len(chunk) == 4:
                    results.append(chunk)

    return results


# ============================================================
# PAGE → LINES
# ============================================================

def html_to_lines(html):
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style noise
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

    lines = []

    for raw in text.splitlines():
        value = clean_text(raw)

        if value:
            lines.append(value)

    return lines


# ============================================================
# FIND PAGE RESULT DATE
#
# This is critical because invalid URLs may return
# another/latest draw.
# ============================================================

def find_page_date(lines):
    for line in lines[:80]:

        match = re.search(
            r"\b(\d{2}/\d{2}/\d{4})\b",
            line
        )

        if match:
            return iso_date(match.group(1))

    return ""


# ============================================================
# OPERATOR DETECTION
# ============================================================

def line_market_key(line):
    low = clean_text(line).lower()

    # Avoid nav line like:
    # Magnum · Toto · DaMaCai ...
    if "·" in low:
        return None

    for key, cfg in MARKETS.items():

        for alias in cfg["aliases"]:

            if alias in low:

                # operator heading shouldn't be huge paragraph
                if len(low) <= 45:
                    return key

    return None


# ============================================================
# SPLIT PAGE INTO MARKET BLOCKS
# ============================================================

def market_blocks(lines):
    blocks = {
        key: []
        for key in MARKETS
    }

    current = None

    for line in lines:

        detected = line_market_key(line)

        if detected:
            current = detected

            blocks[current].append(line)

            continue

        if current:
            blocks[current].append(line)

    return blocks


# ============================================================
# FIND PRIZE VALUE
# ============================================================

def find_single_prize(block, keywords):
    for index, line in enumerate(block):

        low = line.lower()

        if any(
            keyword in low
            for keyword in keywords
        ):

            # Number on same line
            nums = extract_4d_numbers(line)

            if nums:
                return nums[-1]

            # Number normally next line
            for offset in range(
                index + 1,
                min(index + 5, len(block))
            ):

                nums = extract_4d_numbers(
                    block[offset]
                )

                if nums:
                    return nums[0]

    return ""


# ============================================================
# SECTION NUMBERS
# ============================================================

def find_list_prize(
    block,
    start_words,
    stop_words
):
    start_index = None

    for index, line in enumerate(block):

        low = line.lower()

        if any(
            word in low
            for word in start_words
        ):
            start_index = index + 1
            break

    if start_index is None:
        return []

    results = []

    for index in range(
        start_index,
        len(block)
    ):

        line = block[index]
        low = line.lower()

        if any(
            word in low
            for word in stop_words
        ):
            break

        numbers = extract_4d_numbers(line)

        for number in numbers:

            if number not in results:
                results.append(number)

            if len(results) >= 10:
                return results[:10]

    return results[:10]


# ============================================================
# PARSE MARKET
# ============================================================

def parse_market(block, requested_date):

    if not block:
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

    if not (
        first
        and second
        and third
    ):
        return None

    special = find_list_prize(
        block,
        [
            "special"
        ],
        [
            "consolation"
        ]
    )

    consolation = find_list_prize(
        block,
        [
            "consolation"
        ],
        [
            "jackpot",
            "next draw",
            "disclaimer"
        ]
    )

    return {
        "draw": "",
        "date": requested_date,
        "first": normalize_number(first),
        "second": normalize_number(second),
        "third": normalize_number(third),
        "special": [
            normalize_number(x)
            for x in special
        ],
        "consolation": [
            normalize_number(x)
            for x in consolation
        ]
    }


# ============================================================
# RECORD QUALITY
# ============================================================

def record_score(record):
    score = 0

    if record.get("first"):
        score += 5

    if record.get("second"):
        score += 5

    if record.get("third"):
        score += 5

    score += len(
        record.get("special", [])
    )

    score += len(
        record.get("consolation", [])
    )

    return score


# ============================================================
# MERGE RECORD
# ============================================================

def merge_record(database, new_record):

    new_date = new_record.get("date", "")

    for index, old in enumerate(
        database["draws"]
    ):

        if old.get("date") == new_date:

            # Preserve draw number from old DB
            if (
                not new_record.get("draw")
                and old.get("draw")
            ):
                new_record["draw"] = old["draw"]

            if (
                record_score(new_record)
                >
                record_score(old)
            ):
                database["draws"][index] = new_record
                return True

            return False

    database["draws"].append(
        new_record
    )

    return True


# ============================================================
# CLEAN DATABASE
# ============================================================

def clean_database(database):

    deduped = {}

    for record in database["draws"]:

        date = iso_date(
            record.get("date")
        )

        if not date:
            continue

        # Only 2020+
        if date < "2020-01-01":
            continue

        record["date"] = date

        for field in (
            "first",
            "second",
            "third"
        ):
            record[field] = normalize_number(
                record.get(field, "")
            )

        record["special"] = [
            normalize_number(x)
            for x in record.get(
                "special",
                []
            )
            if normalize_number(x)
        ]

        record["consolation"] = [
            normalize_number(x)
            for x in record.get(
                "consolation",
                []
            )
            if normalize_number(x)
        ]

        if date not in deduped:

            deduped[date] = record

        elif (
            record_score(record)
            >
            record_score(deduped[date])
        ):

            deduped[date] = record


    draws = list(
        deduped.values()
    )

    draws.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    database["draws"] = draws

    if draws:

        database["lastUpdated"] = (
            draws[0]["date"]
        )

        database["historyCoverage"] = {
            "drawCount": len(draws),
            "oldestDate": draws[-1]["date"],
            "newestDate": draws[0]["date"]
        }

    else:

        database["historyCoverage"] = {
            "drawCount": 0,
            "oldestDate": "",
            "newestDate": ""
        }

    database["historyRange"] = {
        "from": "2020-01-01",
        "to": TODAY.strftime("%Y-%m-%d")
    }

    database["historySource"] = (
        "4dmanager.net + existing records"
    )


# ============================================================
# SHOULD CHECK DATE?
#
# Normal draw:
# Wed / Sat / Sun
#
# Special draws can occur Tuesday,
# so include Tuesday too.
#
# 0 = Mon
# 1 = Tue
# 2 = Wed
# 5 = Sat
# 6 = Sun
# ============================================================

def should_check_date(dt):
    return dt.weekday() in {
        1,
        2,
        5,
        6
    }


# ============================================================
# HTTP FETCH
# ============================================================

def fetch_page(session, date_value):

    url = BASE_URL.format(
        date=date_value
    )

    response = session.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    return response.text


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 62)
    print("4D CHARTA ANALYZER")
    print("HISTORY BACKFILL V5.0")
    print("2020 → 2026")
    print("=" * 62)


    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    databases = {}

    for key, cfg in MARKETS.items():

        databases[key] = load_database(
            DATA_DIR / cfg["file"],
            cfg["market"]
        )


    # Existing dates allow us to skip
    # records already stored.
    existing_dates = {}

    for key, db in databases.items():

        existing_dates[key] = {
            iso_date(x.get("date"))
            for x in db["draws"]
            if iso_date(x.get("date"))
        }


    session = requests.Session()

    total_pages = 0
    valid_pages = 0
    total_found = 0
    total_changed = 0


    date_cursor = TODAY


    while date_cursor >= START_DATE:

        if not should_check_date(
            date_cursor
        ):
            date_cursor -= timedelta(days=1)
            continue


        date_value = date_cursor.strftime(
            "%Y-%m-%d"
        )


        # Skip network request if ALL 4
        # databases already contain this date.
        already_all = all(
            date_value in existing_dates[key]
            for key in MARKETS
        )


        if already_all:

            date_cursor -= timedelta(days=1)
            continue


        total_pages += 1

        print()
        print(
            f"[{total_pages}] {date_value}"
        )


        try:

            html = fetch_page(
                session,
                date_value
            )

            lines = html_to_lines(html)

        except Exception as error:

            print(
                "  HTTP ERROR:",
                error
            )

            date_cursor -= timedelta(days=1)

            time.sleep(
                REQUEST_DELAY
            )

            continue


        # ----------------------------------------------------
        # CRITICAL VALIDATION
        #
        # Invalid/non-draw date may redirect or display
        # another draw result.
        # ----------------------------------------------------

        page_date = find_page_date(
            lines
        )


        if page_date != date_value:

            print(
                "  skip - page date:",
                page_date or "unknown"
            )

            date_cursor -= timedelta(days=1)

            time.sleep(
                REQUEST_DELAY
            )

            continue


        blocks = market_blocks(
            lines
        )


        found_this_page = 0


        for key, cfg in MARKETS.items():

            record = parse_market(
                blocks.get(key, []),
                date_value
            )


            if not record:
                continue


            found_this_page += 1
            total_found += 1


            changed = merge_record(
                databases[key],
                record
            )


            if changed:
                total_changed += 1


            print(
                f"  ✓ {cfg['market']}: "
                f"{record['first']} "
                f"{record['second']} "
                f"{record['third']} "
                f"| S:{len(record['special'])} "
                f"C:{len(record['consolation'])}"
            )


        if found_this_page:

            valid_pages += 1

        else:

            print(
                "  no supported market parsed"
            )


        time.sleep(
            REQUEST_DELAY
        )

        date_cursor -= timedelta(days=1)


    # ========================================================
    # SAVE
    # ========================================================

    print()
    print("=" * 62)
    print("SAVE DATABASE")
    print("=" * 62)


    for key, cfg in MARKETS.items():

        database = databases[key]

        clean_database(
            database
        )

        save_json(
            DATA_DIR / cfg["file"],
            database
        )

        coverage = database.get(
            "historyCoverage",
            {}
        )


        print()
        print(cfg["market"])

        print(
            "  Draw count :",
            coverage.get(
                "drawCount",
                0
            )
        )

        print(
            "  Oldest     :",
            coverage.get(
                "oldestDate",
                "-"
            )
        )

        print(
            "  Newest     :",
            coverage.get(
                "newestDate",
                "-"
            )
        )


    print()
    print("=" * 62)
    print("BACKFILL COMPLETE")
    print("Pages requested :", total_pages)
    print("Valid pages     :", valid_pages)
    print("Records parsed  :", total_found)
    print("New / changed   :", total_changed)
    print("=" * 62)


if __name__ == "__main__":
    main()
