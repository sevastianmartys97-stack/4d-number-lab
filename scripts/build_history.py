from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

import requests


# ============================================================
# 4D CHARTA ANALYZER
# ONE-TIME HISTORY DATABASE BUILDER
#
# RANGE:
# 2021-01-01 -> 2026-12-31
#
# FULL BULK IMPORT:
# - Magnum
# - Sports Toto
# - Da Ma Cai
#
# CASH SWEEP:
# - Preserve current data only for now
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

START_DATE = "2021-01-01"
END_DATE = "2026-12-31"


SOURCES = {
    "magnum": {
        "market": "Magnum 4D",
        "file": "magnum.json",
        "url": (
            "https://raw.githubusercontent.com/"
            "deadboy18/malaysia-4d/main/data/"
            "magnum_draws.csv"
        ),
    },

    "toto": {
        "market": "Sports Toto",
        "file": "toto.json",
        "url": (
            "https://raw.githubusercontent.com/"
            "deadboy18/malaysia-4d/main/data/"
            "sportstoto_draws.csv"
        ),
    },

    "damacai": {
        "market": "Da Ma Cai",
        "file": "damacai.json",
        "url": (
            "https://raw.githubusercontent.com/"
            "deadboy18/malaysia-4d/main/data/"
            "damacai_draws.csv"
        ),
    },
}


HEADERS = {
    "User-Agent": "Mozilla/5.0 4D-Charta-History-Builder"
}


# ============================================================
# HELPERS
# ============================================================

def normalize4(value):
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    digits = "".join(
        ch for ch in text
        if ch.isdigit()
    )

    if not digits:
        return ""

    return digits[-4:].zfill(4)


def normalize_date(value):
    value = str(value or "").strip()

    if not value:
        return ""

    formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d-%b-%Y",
    )

    for fmt in formats:
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


def record_score(record):
    score = 0

    for key in (
        "first",
        "second",
        "third"
    ):
        if record.get(key):
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
# DOWNLOAD CSV
# ============================================================

def download_csv(url):
    print("Downloading:")
    print(url)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=60
    )

    response.raise_for_status()

    text = response.text

    if len(text) < 1000:
        raise RuntimeError(
            "Downloaded CSV looks too small."
        )

    return text


# ============================================================
# CSV -> DRAW RECORDS
# ============================================================

def parse_csv(text):
    reader = csv.DictReader(
        io.StringIO(text)
    )

    records = []


    for row in reader:

        date_value = normalize_date(
            row.get("date")
        )

        if not date_value:
            continue

        if date_value < START_DATE:
            continue

        if date_value > END_DATE:
            continue


        first = normalize4(
            row.get("prize_1")
        )

        second = normalize4(
            row.get("prize_2")
        )

        third = normalize4(
            row.get("prize_3")
        )


        if not (
            first
            and second
            and third
        ):
            continue


        special = []

        for i in range(
            1,
            11
        ):
            num = normalize4(
                row.get(
                    f"special_{i}"
                )
            )

            if num:
                special.append(num)


        consolation = []

        for i in range(
            1,
            11
        ):
            num = normalize4(
                row.get(
                    f"consol_{i}"
                )
            )

            if num:
                consolation.append(num)


        draw_no = (
            row.get("draw_seq")
            or row.get("draw")
            or row.get("draw_no")
            or ""
        )


        record = {
            "draw": str(
                draw_no
            ).strip(),

            "date": date_value,

            "first": first,
            "second": second,
            "third": third,

            "special":
                special[:10],

            "consolation":
                consolation[:10]
        }


        records.append(record)


    return records


# ============================================================
# MERGE WITH CURRENT JSON
# ============================================================

def merge_records(
    imported,
    existing
):
    by_date = {}


    for record in existing:

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

        if date_value < START_DATE:
            continue

        if date_value > END_DATE:
            continue


        cleaned = {
            "draw":
                str(
                    record.get(
                        "draw",
                        ""
                    )
                ),

            "date":
                date_value,

            "first":
                normalize4(
                    record.get(
                        "first"
                    )
                ),

            "second":
                normalize4(
                    record.get(
                        "second"
                    )
                ),

            "third":
                normalize4(
                    record.get(
                        "third"
                    )
                ),

            "special": [
                normalize4(x)
                for x in record.get(
                    "special",
                    []
                )
                if normalize4(x)
            ],

            "consolation": [
                normalize4(x)
                for x in record.get(
                    "consolation",
                    []
                )
                if normalize4(x)
            ],
        }


        if not (
            cleaned["first"]
            and cleaned["second"]
            and cleaned["third"]
        ):
            continue


        by_date[
            date_value
        ] = cleaned


    for record in imported:

        date_value = record[
            "date"
        ]

        current = by_date.get(
            date_value
        )

        if (
            current is None
            or
            record_score(record)
            >=
            record_score(current)
        ):
            by_date[
                date_value
            ] = record


    draws = list(
        by_date.values()
    )

    draws.sort(
        key=lambda x:
            x["date"],
        reverse=True
    )

    return draws


# ============================================================
# BUILD ONE MARKET
# ============================================================

def build_market(
    key,
    config
):
    print()
    print("=" * 65)
    print(config["market"])
    print("=" * 65)


    path = DATA_DIR / config[
        "file"
    ]


    existing_db = load_json(
        path,
        {
            "market":
                config["market"],

            "draws": []
        }
    )


    existing_draws = (
        existing_db.get(
            "draws",
            []
        )
        if isinstance(
            existing_db,
            dict
        )
        else []
    )


    csv_text = download_csv(
        config["url"]
    )


    imported = parse_csv(
        csv_text
    )


    print(
        "Imported CSV records:",
        len(imported)
    )


    draws = merge_records(
        imported,
        existing_draws
    )


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


    database = {
        "market":
            config["market"],

        "lastUpdated":
            newest,

        "historyCoverage": {
            "drawCount":
                len(draws),

            "oldestDate":
                oldest,

            "newestDate":
                newest,
        },

        "historyRange": {
            "from":
                START_DATE,

            "to":
                END_DATE,
        },

        "historySource":
            "deadboy18/malaysia-4d public historical CSV + existing recent records",

        "draws":
            draws,
    }


    if len(draws) < 200:
        raise RuntimeError(
            f"{key}: only "
            f"{len(draws)} records "
            f"after import."
        )


    if (
        not oldest
        or oldest > "2021-12-31"
    ):
        raise RuntimeError(
            f"{key}: oldest date "
            f"is only {oldest}"
        )


    save_json(
        path,
        database
    )


    print()
    print("SUCCESS")

    print(
        "Draw count:",
        len(draws)
    )

    print(
        "Oldest:",
        oldest
    )

    print(
        "Newest:",
        newest
    )


# ============================================================
# CASH SWEEP
# ============================================================

def preserve_cashsweep():
    print()
    print("=" * 65)
    print("Cash Sweep")
    print("=" * 65)


    path = (
        DATA_DIR
        / "cashsweep.json"
    )


    database = load_json(
        path,
        {
            "market":
                "Cash Sweep",

            "draws": []
        }
    )


    draws = database.get(
        "draws",
        []
    )


    valid = []


    for record in draws:

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


        record["date"] = (
            date_value
        )

        record["first"] = (
            normalize4(
                record.get(
                    "first"
                )
            )
        )

        record["second"] = (
            normalize4(
                record.get(
                    "second"
                )
            )
        )

        record["third"] = (
            normalize4(
                record.get(
                    "third"
                )
            )
        )


        record["special"] = [
            normalize4(x)
            for x in record.get(
                "special",
                []
            )
            if normalize4(x)
        ]


        record["consolation"] = [
            normalize4(x)
            for x in record.get(
                "consolation",
                []
            )
            if normalize4(x)
        ]


        if (
            record["first"]
            and
            record["second"]
            and
            record["third"]
        ):
            valid.append(record)


    valid.sort(
        key=lambda x:
            x["date"],
        reverse=True
    )


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
    ] = "Cash Sweep"


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
            newest,
    }


    # IMPORTANT:
    # Do not claim Cash Sweep has
    # 2021 history until we really
    # have the data.

    database[
        "historyRange"
    ] = {
        "from":
            oldest,

        "to":
            newest,
    }


    database[
        "historySource"
    ] = (
        "Existing Cash Sweep "
        "database only - "
        "historical bulk backfill "
        "still pending"
    )


    database[
        "draws"
    ] = valid


    save_json(
        path,
        database
    )


    print(
        "Preserved:",
        len(valid),
        "draws"
    )

    print(
        "Oldest:",
        oldest
    )

    print(
        "Newest:",
        newest
    )

    print(
        "STATUS: PARTIAL HISTORY"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 65)
    print("4D CHARTA ANALYZER")
    print("ONE-TIME HISTORY BUILDER")
    print("2021 -> 2026")
    print("=" * 65)


    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    for key, config in (
        SOURCES.items()
    ):
        build_market(
            key,
            config
        )


    preserve_cashsweep()


    print()
    print("=" * 65)
    print("FINAL")
    print("=" * 65)

    print(
        "MAGNUM    : FULL BULK HISTORY IMPORTED"
    )

    print(
        "SPORTS TOTO: FULL BULK HISTORY IMPORTED"
    )

    print(
        "DA MA CAI : FULL BULK HISTORY IMPORTED"
    )

    print(
        "CASH SWEEP: CURRENT DATA PRESERVED"
    )

    print()
    print(
        "History builder completed."
    )

    print("=" * 65)


if __name__ == "__main__":
    main()
