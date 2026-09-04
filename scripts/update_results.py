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
# HISTORY AUTO UPDATER V4.4
#
# FIRST RUN:
# - Scan sehingga 90 hari ke belakang
#
# NEXT RUN:
# - Scan 14 hari terakhir sahaja
#
# MARKET:
# - Sports Toto
# - Magnum
# - Da Ma Cai
# - Sarawak Cash Sweep
# =========================================================


ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"

META_FILE = DATA / "update_meta.json"


URL = "https://4d-my.com/4d-past-results/?draw={date}"


MARKETS = {

    "toto": {
        "file": "toto.json",
        "names": [
            "SportsToto 4D",
            "Sports Toto 4D",
            "Sports Toto"
        ]
    },

    "magnum": {
        "file": "magnum.json",
        "names": [
            "Magnum 4D",
            "Magnum4D",
            "Magnum"
        ]
    },

    "damacai": {
        "file": "damacai.json",
        "names": [
            "Da Ma Cai 1+3D",
            "Da Ma Cai",
            "Damacai"
        ]
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "names": [
            "Sarawak Cash Sweep",
            "Cash Sweep"
        ]
    }

}


HEADERS = {

    "User-Agent":
    "Mozilla/5.0 "
    "(Linux; Android 13) "
    "AppleWebKit/537.36 "
    "Chrome/124.0 Safari/537.36"

}


# =========================================================
# SETTINGS
# =========================================================

BACKFILL_DAYS = 90

NORMAL_DAYS = 14

REQUEST_DELAY = 0.25


# =========================================================
# JSON
# =========================================================

def load_json(path: Path, default):

    try:

        with path.open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return default


def save_json(path: Path, data):

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

            return datetime.strptime(
                value,
                fmt
            )

        except ValueError:

            pass


    return None


def normalize_date(value):

    dt = parse_date(value)

    if not dt:

        return str(value)


    return dt.strftime(
        "%Y-%m-%d"
    )


# =========================================================
# NORMALIZE NUMBER
# =========================================================

def normalize_number(value):

    if value is None:

        return None


    value = str(value).strip()


    if re.fullmatch(
        r"\d{1,4}",
        value
    ):

        return value.zfill(4)


    match = re.search(
        r"(?<!\d)(\d{4})(?!\d)",
        value
    )


    if match:

        return match.group(1)


    return None


# =========================================================
# DATABASE
# =========================================================

def load_database(
    path: Path,
    market_name: str
):

    data = load_json(

        path,

        {
            "market": market_name,
            "lastUpdated": "",
            "draws": []
        }

    )


    if not isinstance(
        data,
        dict
    ):

        data = {}


    if not isinstance(
        data.get("draws"),
        list
    ):

        data["draws"] = []


    data.setdefault(
        "market",
        market_name
    )


    data.setdefault(
        "lastUpdated",
        ""
    )


    return data


# =========================================================
# HTML → LINES
# =========================================================

def get_page_lines(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    text = soup.get_text(
        "\n",
        strip=True
    )


    lines = []


    for line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line
        ).strip()


        if line:

            lines.append(line)


    return lines


# =========================================================
# FIND MARKET BLOCK
# =========================================================

def find_market_block(
    lines,
    aliases
):

    aliases_lower = [
        x.lower()
        for x in aliases
    ]


    all_market_names = []


    for config in MARKETS.values():

        for name in config["names"]:

            all_market_names.append(
                name.lower()
            )


    start = None


    for i, line in enumerate(lines):

        value = line.lower().strip()


        if value in aliases_lower:

            start = i

            break


    if start is None:

        return None


    end = len(lines)


    for i in range(
        start + 1,
        len(lines)
    ):

        value = lines[i].lower().strip()


        if value in all_market_names:

            end = i

            break


    return lines[
        start:end
    ]


# =========================================================
# FIND DRAW HEADER
# =========================================================

def parse_draw_header(block):

    for line in block:

        # Example:
        # #416/26(Tue) 01-Sep-2026
        # #5338(Tue) 01-Sep-2026

        match = re.search(

            r"#?\s*"
            r"([0-9]+(?:/[0-9]+)?)"
            r"\s*"
            r"\([A-Za-z]{3}\)"
            r"\s*"
            r"([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})",

            line,

            re.I

        )


        if match:

            draw = match.group(1)

            date = normalize_date(
                match.group(2)
            )


            return draw, date


    return None, None


# =========================================================
# PRIZE FINDER
# =========================================================

def find_prize(
    block,
    labels
):

    for i, line in enumerate(block):

        low = line.lower()


        for label in labels:

            label_low = label.lower()


            if label_low in low:

                # Number on same line
                nums = re.findall(
                    r"(?<!\d)(\d{4})(?!\d)",
                    line
                )


                if nums:

                    return nums[-1]


                # Number on next line
                for j in range(
                    i + 1,
                    min(
                        i + 3,
                        len(block)
                    )
                ):

                    value = normalize_number(
                        block[j]
                    )


                    if value:

                        return value


    return None


# =========================================================
# SPECIAL / CONSOLATION
# =========================================================

def find_section_numbers(
    block,
    section,
    stop_section=None
):

    start = None


    for i, line in enumerate(block):

        if line.lower().strip() == section.lower():

            start = i + 1

            break


    if start is None:

        return []


    end = len(block)


    if stop_section:

        for i in range(
            start,
            len(block)
        ):

            if (
                block[i]
                .lower()
                .strip()
                ==
                stop_section.lower()
            ):

                end = i

                break


    results = []


    for line in block[
        start:end
    ]:

        nums = re.findall(

            r"(?<!\d)"
            r"(\d{4})"
            r"(?!\d)",

            line

        )


        for number in nums:

            if number not in results:

                results.append(
                    number
                )


            if len(results) >= 10:

                return results


    return results


# =========================================================
# PARSE ONE MARKET
# =========================================================

def parse_market(block):

    if not block:

        return None


    draw, date = parse_draw_header(
        block
    )


    if not draw or not date:

        return None


    first = find_prize(

        block,

        [
            "1st Prize",
            "1st",
            "First Prize"
        ]

    )


    second = find_prize(

        block,

        [
            "2nd Prize",
            "2nd",
            "Second Prize"
        ]

    )


    third = find_prize(

        block,

        [
            "3rd Prize",
            "3rd",
            "Third Prize"
        ]

    )


    if not (
        first
        and second
        and third
    ):

        return None


    special = find_section_numbers(

        block,

        "Special",

        "Consolation"

    )


    consolation = find_section_numbers(

        block,

        "Consolation"

    )


    return {

        "date": date,

        "draw": draw,

        "first": first,

        "second": second,

        "third": third,

        "special": special,

        "consolation": consolation

    }


# =========================================================
# MERGE
# =========================================================

def merge_record(
    database,
    new_record
):

    draws = database[
        "draws"
    ]


    new_date = str(
        new_record.get(
            "date",
            ""
        )
    )


    new_draw = str(
        new_record.get(
            "draw",
            ""
        )
    )


    for index, old in enumerate(
        draws
    ):

        old_date = str(
            old.get(
                "date",
                ""
            )
        )


        old_draw = str(
            old.get(
                "draw",
                ""
            )
        )


        if (
            old_date == new_date
            and
            old_draw == new_draw
        ):

            if old != new_record:

                draws[index] = (
                    new_record
                )

                return True


            return False


    draws.append(
        new_record
    )


    return True


# =========================================================
# SORT + DEDUP DATABASE
# =========================================================

def clean_database(
    database
):

    unique = {}


    for draw in database[
        "draws"
    ]:

        key = (

            str(
                draw.get(
                    "date",
                    ""
                )
            ),

            str(
                draw.get(
                    "draw",
                    ""
                )
            )

        )


        unique[key] = draw


    draws = list(
        unique.values()
    )


    def sort_key(draw):

        dt = parse_date(
            draw.get(
                "date"
            )
        )


        if dt:

            return dt


        return datetime.min


    draws.sort(
        key=sort_key,
        reverse=True
    )


    database[
        "draws"
    ] = draws


    dates = [

        parse_date(
            x.get(
                "date"
            )
        )

        for x in draws

    ]


    dates = [
        x
        for x in dates
        if x
    ]


    if dates:

        newest = max(
            dates
        )

        oldest = min(
            dates
        )


        database[
            "lastUpdated"
        ] = newest.strftime(
            "%Y-%m-%d"
        )


        database[
            "historyCoverage"
        ] = {

            "drawCount":
            len(draws),

            "oldestDate":
            oldest.strftime(
                "%Y-%m-%d"
            ),

            "newestDate":
            newest.strftime(
                "%Y-%m-%d"
            )

        }


    else:

        database[
            "historyCoverage"
        ] = {

            "drawCount":
            len(draws),

            "oldestDate":
            "",

            "newestDate":
            ""

        }


# =========================================================
# DOWNLOAD DATE
# =========================================================

def download_date(
    session,
    target_date
):

    url = URL.format(

        date=
        target_date.strftime(
            "%Y-%m-%d"
        )

    )


    response = session.get(

        url,

        headers=HEADERS,

        timeout=25

    )


    response.raise_for_status()


    return response.text


# =========================================================
# MAIN
# =========================================================

def main():

    DATA.mkdir(
        parents=True,
        exist_ok=True
    )


    meta = load_json(

        META_FILE,

        {
            "backfillCompleted": False
        }

    )


    first_backfill = not bool(

        meta.get(
            "backfillCompleted"
        )

    )


    if first_backfill:

        days_to_scan = (
            BACKFILL_DAYS
        )

        print(
            "MODE: 90 DAY HISTORY BACKFILL"
        )

    else:

        days_to_scan = (
            NORMAL_DAYS
        )

        print(
            "MODE: NORMAL UPDATE"
        )


    print(
        "Scanning:",
        days_to_scan,
        "days"
    )


    databases = {}


    for key, config in MARKETS.items():

        file_path = (
            DATA
            /
            config["file"]
        )


        databases[key] = (
            load_database(

                file_path,

                config["names"][0]

            )
        )


    session = requests.Session()


    parsed_dates = 0

    total_updates = 0


    today = datetime.now()


    for day_index in range(
        days_to_scan
    ):

        target_date = (

            today
            -
            timedelta(
                days=day_index
            )

        )


        date_string = (
            target_date.strftime(
                "%Y-%m-%d"
            )
        )


        print(
            "Checking:",
            date_string
        )


        try:

            html = download_date(

                session,

                target_date

            )


            lines = get_page_lines(
                html
            )


            date_has_result = False


            for key, config in MARKETS.items():

                block = find_market_block(

                    lines,

                    config["names"]

                )


                record = parse_market(
                    block
                )


                if not record:

                    continue


                # Safety:
                # result date must match requested date
                result_dt = parse_date(
                    record["date"]
                )


                if result_dt:

                    if (
                        result_dt.date()
                        !=
                        target_date.date()
                    ):

                        continue


                changed = merge_record(

                    databases[key],

                    record

                )


                if changed:

                    total_updates += 1


                date_has_result = True


                print(

                    "  ",

                    key,

                    record["date"],

                    record["draw"],

                    record["first"],

                    record["second"],

                    record["third"]

                )


            if date_has_result:

                parsed_dates += 1


        except Exception as error:

            print(

                "WARNING:",

                date_string,

                str(error)

            )


        time.sleep(
            REQUEST_DELAY
        )


    # =====================================================
    # SAVE ALL DATABASES
    # =====================================================

    for key, config in MARKETS.items():

        database = (
            databases[key]
        )


        clean_database(
            database
        )


        file_path = (

            DATA
            /
            config["file"]

        )


        save_json(

            file_path,

            database

        )


        coverage = database.get(

            "historyCoverage",

            {}

        )


        print()

        print(
            key.upper()
        )

        print(
            "Draw count:",
            coverage.get(
                "drawCount",
                0
            )
        )

        print(
            "Oldest:",
            coverage.get(
                "oldestDate",
                "-"
            )
        )

        print(
            "Newest:",
            coverage.get(
                "newestDate",
                "-"
            )
        )


    # =====================================================
    # META
    # =====================================================

    meta[
        "lastRun"
    ] = datetime.now().strftime(

        "%Y-%m-%d %H:%M:%S"

    )


    meta[
        "lastParsedDates"
    ] = parsed_dates


    meta[
        "lastUpdates"
    ] = total_updates


    if first_backfill:

        # Only mark successful when enough result dates
        # were actually parsed.

        if parsed_dates >= 10:

            meta[
                "backfillCompleted"
            ] = True


            meta[
                "backfillDays"
            ] = BACKFILL_DAYS


            meta[
                "backfillCompletedAt"
            ] = datetime.now().strftime(

                "%Y-%m-%d %H:%M:%S"

            )


            print()

            print(
                "90 DAY BACKFILL COMPLETED ✓"
            )


        else:

            meta[
                "backfillCompleted"
            ] = False


            print()

            print(
                "BACKFILL NOT COMPLETED"
            )

            print(
                "Only",
                parsed_dates,
                "result dates parsed."
            )


    save_json(

        META_FILE,

        meta

    )


    print()

    print(
        "================================"
    )

    print(
        "UPDATE FINISHED"
    )

    print(
        "Result dates:",
        parsed_dates
    )

    print(
        "New/changed records:",
        total_updates
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()
