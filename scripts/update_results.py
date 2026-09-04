from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =========================================================
# 4D CHARTA ANALYZER
# HISTORY UPDATER V4.6
#
# - Scan setiap tarikh 90 hari
# - Simpan hanya tarikh draw sebenar
# - Exact parser ikut heading market
# - Merge, dedupe, sort
# =========================================================


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

URL = "https://4d-my.com/4d-past-results/?draw={date}"

HISTORY_DAYS = 90
REQUEST_DELAY = 0.35


MARKETS = {
    "magnum": {
        "file": "magnum.json",
        "operator": "Magnum",
        "heading": "Magnum 4D"
    },

    "damacai": {
        "file": "damacai.json",
        "operator": "Da Ma Cai",
        "heading": "Da Ma Cai 1+3D"
    },

    "toto": {
        "file": "toto.json",
        "operator": "Sports Toto",
        "heading": "SportsToto 4D"
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "operator": "Cash Sweep",
        "heading": "Sarawak Cash Sweep"
    }
}


HEADERS = {
    "User-Agent":
        "Mozilla/5.0 "
        "(Linux; Android 13) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
}


# =========================================================
# JSON
# =========================================================

def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )
        f.write("\n")


# =========================================================
# DATE
# =========================================================

def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%d %b %Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def normalize_date(value):
    dt = parse_date(value)

    if not dt:
        return str(value)

    return dt.strftime("%Y-%m-%d")


# =========================================================
# DATABASE
# =========================================================

def load_database(path: Path, operator_name: str):
    data = load_json(
        path,
        {
            "operator": operator_name,
            "game": "4D",
            "lastUpdated": "",
            "source": "Historical 4D Results",
            "draws": []
        }
    )

    if not isinstance(data, dict):
        data = {}

    if not isinstance(data.get("draws"), list):
        data["draws"] = []

    data.setdefault("operator", operator_name)
    data.setdefault("game", "4D")
    data.setdefault("source", "Historical 4D Results")
    data.setdefault("lastUpdated", "")

    return data


# =========================================================
# NORMALIZE TEXT
# =========================================================

def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


# =========================================================
# GET PAGE TEXT AS LINES
# =========================================================

def get_lines(html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        "\n",
        strip=True
    )

    return [
        clean_text(x)
        for x in text.splitlines()
        if clean_text(x)
    ]


# =========================================================
# FIND EXACT MARKET BLOCK
# =========================================================

def get_market_block(lines, market_heading):
    headings = [
        cfg["heading"]
        for cfg in MARKETS.values()
    ]

    start = None

    for i, line in enumerate(lines):
        if line.lower() == market_heading.lower():
            start = i
            break

    if start is None:
        return []

    end = len(lines)

    for i in range(start + 1, len(lines)):
        line = lines[i]

        for heading in headings:
            if line.lower() == heading.lower():
                end = i
                return lines[start:end]

        # Also stop at other operator headings
        if line in [
            "GD Lotto",
            "Sabah 4D88",
            "Sandakan STC 4D",
            "Singapore Pools 4D"
        ]:
            end = i
            return lines[start:end]

    return lines[start:end]


# =========================================================
# DRAW HEADER
# =========================================================

def parse_header(block):
    for line in block:
        m = re.search(
            r"#?\s*"
            r"([0-9]+(?:/[0-9]+)?)"
            r"\s*"
            r"\([A-Za-z]{3}\)"
            r"\s*"
            r"([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})",
            line,
            re.I
        )

        if m:
            return {
                "draw": m.group(1),
                "date": normalize_date(
                    m.group(2)
                )
            }

    return None


# =========================================================
# FIND SINGLE PRIZE
# =========================================================

def find_prize(block, label_words):
    for i, line in enumerate(block):
        low = line.lower()

        if any(
            label.lower() in low
            for label in label_words
        ):
            nums = re.findall(
                r"(?<!\d)(\d{4})(?!\d)",
                line
            )

            if nums:
                return nums[-1]

            # usually number may be next line
            for j in range(
                i + 1,
                min(i + 4, len(block))
            ):
                nums2 = re.findall(
                    r"(?<!\d)(\d{4})(?!\d)",
                    block[j]
                )

                if nums2:
                    return nums2[0]

    return None


# =========================================================
# FIND SPECIAL / CONSOLATION
# =========================================================

def find_section(
    block,
    start_label,
    stop_label=None
):
    start = None

    for i, line in enumerate(block):
        if line.lower() == start_label.lower():
            start = i + 1
            break

    if start is None:
        return []

    end = len(block)

    if stop_label:
        for i in range(start, len(block)):
            if block[i].lower() == stop_label.lower():
                end = i
                break

    results = []

    for line in block[start:end]:
        found = re.findall(
            r"(?<!\d)(\d{4})(?!\d)",
            line
        )

        for number in found:
            if number not in results:
                results.append(number)

            if len(results) == 10:
                return results

    return results


# =========================================================
# PARSE ONE MARKET
# =========================================================

def parse_market(lines, config):
    block = get_market_block(
        lines,
        config["heading"]
    )

    if not block:
        return None

    header = parse_header(block)

    if not header:
        return None

    first = find_prize(
        block,
        [
            "1st Prize",
            "1st"
        ]
    )

    second = find_prize(
        block,
        [
            "2nd Prize",
            "2nd"
        ]
    )

    third = find_prize(
        block,
        [
            "3rd Prize",
            "3rd"
        ]
    )

    if not (
        first
        and second
        and third
    ):
        return None

    special = find_section(
        block,
        "Special",
        "Consolation"
    )

    consolation = find_section(
        block,
        "Consolation"
    )

    return {
        "draw": header["draw"],
        "date": header["date"],
        "first": first,
        "second": second,
        "third": third,
        "special": special,
        "consolation": consolation
    }


# =========================================================
# MERGE
# =========================================================

def record_score(record):
    score = 0

    if record.get("first"):
        score += 1

    if record.get("second"):
        score += 1

    if record.get("third"):
        score += 1

    score += len(
        record.get("special", [])
    )

    score += len(
        record.get(
            "consolation",
            []
        )
    )

    return score


def merge_record(database, new_record):
    draws = database["draws"]

    new_date = str(
        new_record.get("date", "")
    )

    new_draw = str(
        new_record.get("draw", "")
    )

    for i, old in enumerate(draws):
        old_date = str(
            old.get("date", "")
        )

        old_draw = str(
            old.get("draw", "")
        )

        same = (
            (
                new_draw
                and old_draw
                and new_draw == old_draw
            )
            or
            (
                new_date
                and old_date
                and new_date == old_date
            )
        )

        if same:
            if (
                record_score(new_record)
                >=
                record_score(old)
            ):
                if old != new_record:
                    draws[i] = new_record
                    return True

            return False

    draws.append(
        new_record
    )

    return True


# =========================================================
# CLEAN / SORT
# =========================================================

def clean_database(database):
    unique = {}

    for draw in database["draws"]:
        key = (
            str(draw.get("date", "")),
            str(draw.get("draw", ""))
        )

        if key not in unique:
            unique[key] = draw
        else:
            if (
                record_score(draw)
                >
                record_score(unique[key])
            ):
                unique[key] = draw

    draws = list(
        unique.values()
    )

    def sort_key(draw):
        dt = parse_date(
            draw.get("date")
        )

        return dt or datetime.min

    draws.sort(
        key=sort_key,
        reverse=True
    )

    database["draws"] = draws

    dates = []

    for draw in draws:
        dt = parse_date(
            draw.get("date")
        )

        if dt:
            dates.append(dt)

    if dates:
        newest = max(dates)
        oldest = min(dates)

        database["lastUpdated"] = (
            newest.strftime("%Y-%m-%d")
        )

        database["historyCoverage"] = {
            "drawCount": len(draws),
            "oldestDate":
                oldest.strftime("%Y-%m-%d"),
            "newestDate":
                newest.strftime("%Y-%m-%d")
        }

    else:
        database["historyCoverage"] = {
            "drawCount": len(draws),
            "oldestDate": "",
            "newestDate": ""
        }


# =========================================================
# FETCH PAGE
# =========================================================

def fetch_date(session, date_value):
    url = URL.format(
        date=date_value
    )

    response = session.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 50)
    print("4D HISTORY UPDATER V4.6")
    print("90 DAY DIRECT DATE SCAN")
    print("=" * 50)

    DATA.mkdir(
        parents=True,
        exist_ok=True
    )

    databases = {}

    for key, config in MARKETS.items():
        databases[key] = load_database(
            DATA / config["file"],
            config["operator"]
        )

    session = requests.Session()

    total_valid_dates = 0
    total_records = 0
    total_changes = 0

    today = datetime.now()

    for day_index in range(HISTORY_DAYS):

        target = (
            today
            -
            timedelta(days=day_index)
        )

        date_value = target.strftime(
            "%Y-%m-%d"
        )

        print()
        print(
            f"[{day_index + 1}/{HISTORY_DAYS}] "
            f"{date_value}"
        )

        try:
            html = fetch_date(
                session,
                date_value
            )

            lines = get_lines(html)

        except Exception as error:
            print(
                "  FETCH ERROR:",
                error
            )

            time.sleep(
                REQUEST_DELAY
            )
            continue


        records_this_date = 0


        for key, config in MARKETS.items():

            record = parse_market(
                lines,
                config
            )

            if not record:
                continue


            # =================================================
            # CRITICAL CHECK
            #
            # Site may return latest result
            # for an invalid/non-draw date.
            #
            # Only save if result date
            # EXACTLY equals requested date.
            # =================================================

            if (
                record["date"]
                !=
                date_value
            ):
                continue


            records_this_date += 1
            total_records += 1


            changed = merge_record(
                databases[key],
                record
            )


            if changed:
                total_changes += 1


            print(
                "  ✓",
                key.upper(),
                record["draw"],
                record["first"],
                record["second"],
                record["third"],
                "S:",
                len(record["special"]),
                "C:",
                len(record["consolation"])
            )


        if records_this_date:
            total_valid_dates += 1

            print(
                "  DRAW DATE ✓"
            )
        else:
            print(
                "  no valid target-market result"
            )


        time.sleep(
            REQUEST_DELAY
        )


    print()
    print("=" * 50)
    print("SAVING DATABASE")
    print("=" * 50)


    for key, config in MARKETS.items():

        database = databases[key]

        clean_database(
            database
        )

        save_json(
            DATA / config["file"],
            database
        )

        coverage = database.get(
            "historyCoverage",
            {}
        )

        print()
        print(key.upper())

        print(
            " Draw count:",
            coverage.get(
                "drawCount",
                0
            )
        )

        print(
            " Oldest:",
            coverage.get(
                "oldestDate",
                "-"
            )
        )

        print(
            " Newest:",
            coverage.get(
                "newestDate",
                "-"
            )
        )


    print()
    print("=" * 50)
    print("V4.6 FINISHED ✓")
    print(
        "Valid draw dates:",
        total_valid_dates
    )
    print(
        "Records parsed:",
        total_records
    )
    print(
        "New / changed:",
        total_changes
    )
    print("=" * 50)


if __name__ == "__main__":
    main()
