from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import requests


# ============================================================
# 4D CHARTA ANALYZER
# HISTORY UPDATER V6.0 - API EDITION
#
# SOURCE:
# https://4dresult.asia public REST API
#
# RANGE:
# 2020-01-01 -> current date
#
# MARKETS:
# - Magnum
# - Sports Toto
# - Da Ma Cai
# - Cash Sweep
#
# IMPORTANT:
# - Uses official published API structure
# - Does NOT scrape HTML
# - Gets real archive draw dates first
# - Then gets full result for each draw date
# - Preserves leading zeroes
# - Merges with existing JSON
# - Workflow FAILS if historical backfill is clearly unsuccessful
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

API_BASE = "https://4dresult.asia/api/results"

START_YEAR = 2020
CURRENT_YEAR = datetime.now().year
TODAY = datetime.now().strftime("%Y-%m-%d")

REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.12
MAX_RETRIES = 3


MARKETS = {
    "magnum": {
        "file": "magnum.json",
        "market": "Magnum 4D"
    },

    "toto": {
        "file": "toto.json",
        "market": "Sports Toto"
    },

    "damacai": {
        "file": "damacai.json",
        "market": "Da Ma Cai"
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "market": "Cash Sweep"
    }
}


HEADERS = {
    "User-Agent": "4D-Charta-Analyzer/6.0",
    "Accept": "application/json"
}


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
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
# NUMBER NORMALIZATION
# ============================================================

def normalize4(value):
    if value is None:
        return ""

    text = "".join(
        ch for ch in str(value)
        if ch.isdigit()
    )

    if not text:
        return ""

    return text[-4:].zfill(4)


def normalize_list(values):
    if not isinstance(values, list):
        return []

    output = []

    for value in values:
        number = normalize4(value)

        if (
            number
            and number not in output
        ):
            output.append(number)

    return output


# ============================================================
# HTTP
# ============================================================

def api_get(session, url, params=None):

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()

            data = response.json()

            return data

        except Exception as error:

            last_error = error

            print(
                f"    retry {attempt}/{MAX_RETRIES}:",
                error
            )

            time.sleep(
                1.0 * attempt
            )

    raise RuntimeError(
        f"API request failed: {url} | {last_error}"
    )


# ============================================================
# GET ARCHIVE DATES
#
# We DO NOT scan every calendar day.
#
# API returns actual published draw dates.
# ============================================================

def get_archive_dates(session):

    dates = set()

    print()
    print("=" * 65)
    print("FETCH ARCHIVE DATES")
    print("=" * 65)

    for year in range(
        START_YEAR,
        CURRENT_YEAR + 1
    ):

        url = (
            API_BASE
            + "/archive"
        )

        params = {
            "country_code": "MY",
            "year": str(year),
            "limit": 500,
            "offset": 0
        }

        data = api_get(
            session,
            url,
            params
        )

        if not data:
            print(
                year,
                "-> no archive data"
            )
            continue

        entries = data.get(
            "dates",
            []
        )

        count = 0

        for item in entries:

            if not isinstance(
                item,
                dict
            ):
                continue

            date_value = str(
                item.get(
                    "date",
                    ""
                )
            )

            if not date_value:
                continue

            if date_value < "2020-01-01":
                continue

            if date_value > TODAY:
                continue

            providers = item.get(
                "providers",
                []
            )

            # Keep only dates involving
            # at least one target provider.
            if isinstance(
                providers,
                list
            ):

                target_found = any(
                    str(provider).lower()
                    in MARKETS
                    for provider in providers
                )

                if not target_found:
                    continue

            dates.add(
                date_value
            )

            count += 1

        print(
            f"{year}: {count} draw dates"
        )

        time.sleep(
            REQUEST_DELAY
        )

    result = sorted(
        dates,
        reverse=True
    )

    print()
    print(
        "TOTAL UNIQUE DRAW DATES:",
        len(result)
    )

    return result


# ============================================================
# TOP PRIZES
# ============================================================

def extract_top_prizes(prizes):

    first = ""
    second = ""
    third = ""

    top = prizes.get(
        "top",
        []
    )

    if not isinstance(
        top,
        list
    ):
        top = []

    for item in top:

        if not isinstance(
            item,
            dict
        ):
            continue

        prize = str(
            item.get(
                "prize",
                ""
            )
        ).lower()

        number = normalize4(
            item.get(
                "number",
                ""
            )
        )

        if not number:
            continue

        if "1st" in prize:
            first = number

        elif "2nd" in prize:
            second = number

        elif "3rd" in prize:
            third = number

    return (
        first,
        second,
        third
    )


# ============================================================
# PARSE PROVIDER RESULT
# ============================================================

def parse_provider_result(
    result,
    draw_date
):

    if not isinstance(
        result,
        dict
    ):
        return None, None

    provider_code = str(
        result.get(
            "provider_code",
            ""
        )
    ).lower().strip()

    if provider_code not in MARKETS:
        return None, None

    prizes = result.get(
        "prizes",
        {}
    )

    if not isinstance(
        prizes,
        dict
    ):
        return None, None

    first, second, third = (
        extract_top_prizes(
            prizes
        )
    )

    # A valid board must contain
    # all Top 3 prizes.
    if not (
        first
        and second
        and third
    ):
        return None, None

    special = normalize_list(
        prizes.get(
            "special",
            []
        )
    )

    consolation = normalize_list(
        prizes.get(
            "consolation",
            []
        )
    )

    record = {
        "draw": str(
            result.get(
                "draw_number",
                ""
            )
        ),
        "date": draw_date,
        "first": first,
        "second": second,
        "third": third,
        "special": special,
        "consolation": consolation
    }

    return (
        provider_code,
        record
    )


# ============================================================
# RECORD QUALITY
# ============================================================

def record_score(record):

    score = 0

    if record.get("first"):
        score += 10

    if record.get("second"):
        score += 10

    if record.get("third"):
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
# MERGE RECORD
# ============================================================

def merge_record(
    database,
    new_record
):

    new_date = new_record.get(
        "date",
        ""
    )

    new_draw = new_record.get(
        "draw",
        ""
    )

    for index, old in enumerate(
        database["draws"]
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

        same_record = (
            old_date == new_date
        )

        if (
            new_draw
            and old_draw
            and new_draw == old_draw
        ):
            same_record = True

        if not same_record:
            continue

        # Replace if API record is at least
        # as complete as existing record.
        if (
            record_score(
                new_record
            )
            >=
            record_score(
                old
            )
        ):

            if old != new_record:

                database[
                    "draws"
                ][index] = new_record

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

    for record in database[
        "draws"
    ]:

        if not isinstance(
            record,
            dict
        ):
            continue

        date_value = str(
            record.get(
                "date",
                ""
            )
        )

        if (
            not date_value
            or date_value < "2020-01-01"
            or date_value > TODAY
        ):
            continue

        clean = {
            "draw": str(
                record.get(
                    "draw",
                    ""
                )
            ),
            "date": date_value,

            "first": normalize4(
                record.get(
                    "first",
                    ""
                )
            ),

            "second": normalize4(
                record.get(
                    "second",
                    ""
                )
            ),

            "third": normalize4(
                record.get(
                    "third",
                    ""
                )
            ),

            "special": normalize_list(
                record.get(
                    "special",
                    []
                )
            ),

            "consolation":
                normalize_list(
                    record.get(
                        "consolation",
                        []
                    )
                )
        }

        if not (
            clean["first"]
            and clean["second"]
            and clean["third"]
        ):
            continue

        key = (
            clean["date"],
            clean["draw"]
        )

        if key not in unique:

            unique[key] = clean

        elif (
            record_score(clean)
            >
            record_score(
                unique[key]
            )
        ):

            unique[key] = clean


    draws = list(
        unique.values()
    )

    draws.sort(
        key=lambda x:
            x["date"],
        reverse=True
    )

    database["draws"] = draws


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
        "4dresult.asia public API"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("4D CHARTA ANALYZER")
    print("HISTORY UPDATER V6.0")
    print("PUBLIC API / 2020 -> CURRENT")
    print("=" * 65)


    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    databases = {}

    for key, cfg in MARKETS.items():

        databases[key] = (
            load_database(
                DATA_DIR
                / cfg["file"],
                cfg["market"]
            )
        )


    session = requests.Session()


    # ========================================================
    # STEP 1
    # Get real archive dates
    # ========================================================

    draw_dates = (
        get_archive_dates(
            session
        )
    )


    # Critical safety check.
    if len(draw_dates) < 50:

        raise RuntimeError(
            "Archive validation FAILED: "
            f"only {len(draw_dates)} "
            "historical dates returned."
        )


    # We specifically asked for 2020+.
    oldest_archive = min(
        draw_dates
    )

    print(
        "Oldest archive date:",
        oldest_archive
    )


    if oldest_archive > "2020-12-31":

        raise RuntimeError(
            "Archive validation FAILED: "
            "source did not reach year 2020."
        )


    # ========================================================
    # STEP 2
    # Fetch complete result boards
    # ========================================================

    print()
    print("=" * 65)
    print("FETCH FULL DRAW RESULTS")
    print("=" * 65)


    total_dates = 0
    total_records = 0
    total_changes = 0


    for index, draw_date in enumerate(
        draw_dates,
        start=1
    ):

        print(
            f"[{index}/{len(draw_dates)}] "
            f"{draw_date}"
        )


        url = (
            API_BASE
            + "/by-date/MY/"
            + draw_date
        )


        try:

            data = api_get(
                session,
                url
            )

        except Exception as error:

            print(
                "  ERROR:",
                error
            )

            continue


        if not data:
            print(
                "  no result"
            )
            continue


        returned_date = str(
            data.get(
                "draw_date",
                ""
            )
        )


        # Exact date validation.
        if returned_date != draw_date:

            print(
                "  DATE MISMATCH:",
                returned_date
            )

            continue


        results = data.get(
            "results",
            []
        )


        if not isinstance(
            results,
            list
        ):
            continue


        records_this_date = 0


        for result in results:

            (
                provider_code,
                record
            ) = parse_provider_result(
                result,
                draw_date
            )


            if (
                not provider_code
                or not record
            ):
                continue


            records_this_date += 1
            total_records += 1


            changed = merge_record(
                databases[
                    provider_code
                ],
                record
            )


            if changed:
                total_changes += 1


            print(
                "   ✓",
                provider_code.upper(),
                record["draw"],
                record["first"],
                record["second"],
                record["third"],
                f"S:{len(record['special'])}",
                f"C:{len(record['consolation'])}"
            )


        if records_this_date:

            total_dates += 1


        time.sleep(
            REQUEST_DELAY
        )


    # ========================================================
    # STEP 3
    # Clean and save
    # ========================================================

    print()
    print("=" * 65)
    print("SAVE DATABASE")
    print("=" * 65)


    final_counts = {}


    for key, cfg in MARKETS.items():

        database = databases[
            key
        ]


        clean_database(
            database
        )


        coverage = database[
            "historyCoverage"
        ]


        final_counts[key] = (
            coverage[
                "drawCount"
            ]
        )


        save_json(
            DATA_DIR
            / cfg["file"],
            database
        )


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


    # ========================================================
    # FINAL VALIDATION
    #
    # Do not allow fake GREEN success
    # like previous updater.
    # ========================================================

    failed_markets = []


    for key, count in (
        final_counts.items()
    ):

        if count < 50:

            failed_markets.append(
                f"{key}={count}"
            )


    oldest_dates = [
        databases[key]
        ["historyCoverage"]
        ["oldestDate"]

        for key in MARKETS

        if databases[key]
        ["historyCoverage"]
        ["oldestDate"]
    ]


    overall_oldest = (
        min(oldest_dates)
        if oldest_dates
        else ""
    )


    if failed_markets:

        raise RuntimeError(
            "BACKFILL FAILED. "
            "Too few historical draws: "
            + ", ".join(
                failed_markets
            )
        )


    if (
        not overall_oldest
        or overall_oldest
        > "2020-12-31"
    ):

        raise RuntimeError(
            "BACKFILL FAILED. "
            "Database did not reach 2020."
        )


    print()
    print("=" * 65)
    print("V6 BACKFILL SUCCESS ✓")
    print("=" * 65)

    print(
        "Archive dates :",
        len(draw_dates)
    )

    print(
        "Valid dates   :",
        total_dates
    )

    print(
        "Records parsed:",
        total_records
    )

    print(
        "New / changed :",
        total_changes
    )

    print(
        "Oldest overall:",
        overall_oldest
    )

    print("=" * 65)


if __name__ == "__main__":
    main()
