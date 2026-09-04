from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# =========================================================
# 4D CHARTA ANALYZER
# HISTORY UPDATER V4.5
#
# CARA BARU:
# - Buka archive
# - Ikut link "Older"
# - Simpan semua draw dalam tempoh ~90 hari
# - Merge dengan data lama
# - Tidak delete rekod lama
# =========================================================


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BASE_URL = "https://4d-my.com"
START_URL = "https://4d-my.com/4d-past-results/"


MARKETS = {

    "toto": {
        "file": "toto.json",
        "operator": "Sports Toto",
        "aliases": [
            "SportsToto 4D",
            "Sports Toto 4D",
            "Sports Toto"
        ]
    },

    "magnum": {
        "file": "magnum.json",
        "operator": "Magnum",
        "aliases": [
            "Magnum 4D",
            "Magnum4D",
            "Magnum"
        ]
    },

    "damacai": {
        "file": "damacai.json",
        "operator": "Da Ma Cai",
        "aliases": [
            "Da Ma Cai 1+3D",
            "Da Ma Cai",
            "Damacai"
        ]
    },

    "cashsweep": {
        "file": "cashsweep.json",
        "operator": "Cash Sweep",
        "aliases": [
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


# Archive website says 90 days.
HISTORY_DAYS = 90

# Safety supaya workflow tidak looping tanpa henti.
MAX_PAGES = 100

REQUEST_DELAY = 0.35


# =========================================================
# BASIC JSON
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
        "%d %b %Y",
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
# NUMBER
# =========================================================

def normalize_number(value):

    if value is None:
        return None

    s = str(value).strip()

    if re.fullmatch(r"\d{1,4}", s):
        return s.zfill(4)

    m = re.search(
        r"(?<!\d)(\d{4})(?!\d)",
        s
    )

    if m:
        return m.group(1)

    return None


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

    data.setdefault(
        "operator",
        operator_name
    )

    data.setdefault(
        "game",
        "4D"
    )

    data.setdefault(
        "source",
        "Historical 4D Results"
    )

    data.setdefault(
        "lastUpdated",
        ""
    )

    return data


# =========================================================
# FIND MARKET SECTIONS FROM HTML
# =========================================================

def extract_market_sections(soup):

    sections = {}

    headings = soup.find_all(
        ["h3", "h2"]
    )

    for heading in headings:

        name = heading.get_text(
            " ",
            strip=True
        )

        if not name:
            continue

        matched_key = None

        for key, cfg in MARKETS.items():

            for alias in cfg["aliases"]:

                if name.strip().lower() == alias.lower():

                    matched_key = key
                    break

            if matched_key:
                break

        if not matched_key:
            continue

        block_parts = []

        node = heading.next_sibling

        while node:

            # Stop apabila jumpa heading market berikutnya.
            if getattr(node, "name", None) in ["h2", "h3"]:

                next_title = node.get_text(
                    " ",
                    strip=True
                )

                is_market = False

                for cfg in MARKETS.values():

                    for alias in cfg["aliases"]:

                        if (
                            next_title.strip().lower()
                            ==
                            alias.lower()
                        ):
                            is_market = True
                            break

                    if is_market:
                        break

                if is_market:
                    break

            if hasattr(node, "get_text"):

                text = node.get_text(
                    "\n",
                    strip=True
                )

                if text:
                    block_parts.append(text)

            else:

                text = str(node).strip()

                if text:
                    block_parts.append(text)

            node = node.next_sibling

        sections[matched_key] = "\n".join(
            block_parts
        )

    return sections


# =========================================================
# FALLBACK TEXT SECTION
# =========================================================

def extract_market_sections_from_text(soup):

    text = soup.get_text(
        "\n",
        strip=True
    )

    lines = [
        re.sub(r"\s+", " ", x).strip()
        for x in text.splitlines()
        if x.strip()
    ]

    sections = {}

    all_aliases = {}

    for key, cfg in MARKETS.items():

        for alias in cfg["aliases"]:

            all_aliases[
                alias.lower()
            ] = key

    for i, line in enumerate(lines):

        key = all_aliases.get(
            line.lower()
        )

        if not key:
            continue

        end = len(lines)

        for j in range(
            i + 1,
            len(lines)
        ):

            if lines[j].lower() in all_aliases:

                end = j
                break

        sections[key] = "\n".join(
            lines[i + 1:end]
        )

    return sections


# =========================================================
# PARSE MARKET BLOCK
# =========================================================

def parse_market_block(block):

    if not block:
        return None

    text = re.sub(
        r"\r",
        "",
        block
    )

    # Examples:
    # #416/26(Tue) 01-Sep-2026
    # #5338(Tue) 01-Sep-2026

    header = re.search(
        r"#?\s*"
        r"([0-9]+(?:/[0-9]+)?)"
        r"\s*"
        r"\([A-Za-z]{3}\)"
        r"\s*"
        r"([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})",
        text,
        re.I
    )

    if not header:
        return None

    draw = header.group(1)

    date = normalize_date(
        header.group(2)
    )

    first = find_prize(
        text,
        [
            "1st Prize",
            "1st",
        ]
    )

    second = find_prize(
        text,
        [
            "2nd Prize",
            "2nd",
        ]
    )

    third = find_prize(
        text,
        [
            "3rd Prize",
            "3rd",
        ]
    )

    if not (
        first
        and second
        and third
    ):
        return None

    special = extract_prize_section(
        text,
        "Special",
        "Consolation"
    )

    consolation = extract_prize_section(
        text,
        "Consolation",
        None
    )

    return {
        "draw": draw,
        "date": date,
        "first": first,
        "second": second,
        "third": third,
        "special": special[:10],
        "consolation": consolation[:10],
    }


# =========================================================
# FIND PRIZES
# =========================================================

def find_prize(text, labels):

    lines = [
        re.sub(r"\s+", " ", x).strip()
        for x in text.splitlines()
        if x.strip()
    ]

    for i, line in enumerate(lines):

        low = line.lower()

        if any(
            label.lower() in low
            for label in labels
        ):

            nums = re.findall(
                r"(?<!\d)(\d{4})(?!\d)",
                line
            )

            if nums:
                return nums[-1]

            for j in range(
                i + 1,
                min(
                    i + 4,
                    len(lines)
                )
            ):

                n = normalize_number(
                    lines[j]
                )

                if n:
                    return n

    return None


# =========================================================
# SPECIAL / CONSOLATION
# =========================================================

def extract_prize_section(
    text,
    section_name,
    stop_name
):

    lines = [
        re.sub(r"\s+", " ", x).strip()
        for x in text.splitlines()
        if x.strip()
    ]

    start = None

    for i, line in enumerate(lines):

        if (
            section_name.lower()
            in line.lower()
        ):

            start = i + 1
            break

    if start is None:
        return []

    end = len(lines)

    if stop_name:

        for i in range(
            start,
            len(lines)
        ):

            if (
                stop_name.lower()
                in lines[i].lower()
            ):

                end = i
                break

    nums = []

    for line in lines[start:end]:

        found = re.findall(
            r"(?<!\d)(\d{4})(?!\d)",
            line
        )

        for n in found:

            if n not in nums:

                nums.append(n)

            if len(nums) >= 10:
                return nums

    return nums


# =========================================================
# MERGE
# =========================================================

def merge_record(database, record):

    draws = database["draws"]

    new_draw = str(
        record.get(
            "draw",
            ""
        )
    )

    new_date = str(
        record.get(
            "date",
            ""
        )
    )

    for i, old in enumerate(draws):

        old_draw = str(
            old.get(
                "draw",
                ""
            )
        )

        old_date = str(
            old.get(
                "date",
                ""
            )
        )

        same_draw = (
            new_draw
            and old_draw
            and new_draw == old_draw
        )

        same_date = (
            new_date
            and old_date
            and new_date == old_date
        )

        if same_draw or same_date:

            # Ganti hanya jika rekod baru lebih lengkap.
            old_score = record_score(old)
            new_score = record_score(record)

            if new_score >= old_score:

                if old != record:

                    draws[i] = record
                    return True

            return False

    draws.append(record)

    return True


def record_score(record):

    score = 0

    if record.get("first"):
        score += 1

    if record.get("second"):
        score += 1

    if record.get("third"):
        score += 1

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


# =========================================================
# CLEAN DATABASE
# =========================================================

def clean_database(database):

    unique = {}

    for draw in database["draws"]:

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

    def key_fn(draw):

        dt = parse_date(
            draw.get("date")
        )

        return dt or datetime.min

    draws.sort(
        key=key_fn,
        reverse=True
    )

    database["draws"] = draws

    dates = []

    for draw in draws:

        dt = parse_date(
            draw.get(
                "date"
            )
        )

        if dt:
            dates.append(dt)

    if dates:

        newest = max(dates)
        oldest = min(dates)

        database[
            "lastUpdated"
        ] = newest.strftime(
            "%Y-%m-%d"
        )

        database[
            "historyCoverage"
        ] = {
            "drawCount": len(draws),
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
            "drawCount": len(draws),
            "oldestDate": "",
            "newestDate": ""
        }


# =========================================================
# FIND PAGE DATE
# =========================================================

def find_page_date(soup):

    text = soup.get_text(
        " ",
        strip=True
    )

    matches = re.findall(
        r"\b"
        r"(\d{1,2}-[A-Za-z]{3}-\d{4})"
        r"\b",
        text
    )

    if not matches:
        return None

    dates = []

    for value in matches:

        dt = parse_date(value)

        if dt:
            dates.append(dt)

    if not dates:
        return None

    # Semua market dalam page biasanya tarikh sama.
    return dates[0]


# =========================================================
# FIND OLDER LINK
# =========================================================

def find_older_url(soup, current_url):

    for a in soup.find_all(
        "a",
        href=True
    ):

        label = a.get_text(
            " ",
            strip=True
        ).lower()

        if label == "older":

            return urljoin(
                current_url,
                a["href"]
            )

    return None


# =========================================================
# FETCH
# =========================================================

def fetch_page(session, url):

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

    print(
        "========================================"
    )

    print(
        "4D HISTORY UPDATER V4.5"
    )

    print(
        "MODE: FOLLOW ARCHIVE OLDER LINKS"
    )

    print(
        "========================================"
    )


    DATA.mkdir(
        parents=True,
        exist_ok=True
    )


    databases = {}

    for key, cfg in MARKETS.items():

        databases[key] = load_database(
            DATA / cfg["file"],
            cfg["operator"]
        )


    session = requests.Session()


    # Mulakan dari latest archive.
    current_url = START_URL

    visited_urls = set()

    total_pages = 0
    total_records_seen = 0
    total_changes = 0


    newest_archive_date = None

    cutoff_date = (
        datetime.now()
        -
        timedelta(
            days=HISTORY_DAYS
        )
    )


    while (
        current_url
        and total_pages < MAX_PAGES
    ):

        if current_url in visited_urls:

            print(
                "STOP: repeated URL"
            )

            break


        visited_urls.add(
            current_url
        )


        print()
        print(
            "PAGE:",
            current_url
        )


        try:

            html = fetch_page(
                session,
                current_url
            )

        except Exception as error:

            print(
                "FETCH ERROR:",
                error
            )

            break


        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        page_date = find_page_date(
            soup
        )


        if page_date:

            print(
                "DATE:",
                page_date.strftime(
                    "%Y-%m-%d"
                )
            )


            if newest_archive_date is None:

                newest_archive_date = page_date


            if (
                page_date
                <
                cutoff_date
            ):

                print(
                    "Reached 90-day cutoff."
                )

                break


        # First parser
        sections = extract_market_sections(
            soup
        )


        # Fallback parser
        if len(sections) < 2:

            fallback = (
                extract_market_sections_from_text(
                    soup
                )
            )

            for k, v in fallback.items():

                sections.setdefault(
                    k,
                    v
                )


        found_this_page = 0


        for key, cfg in MARKETS.items():

            block = sections.get(
                key
            )


            if not block:
                continue


            record = parse_market_block(
                block
            )


            if not record:
                continue


            # Safety: if page date exists,
            # result date should match.
            record_dt = parse_date(
                record.get(
                    "date"
                )
            )


            if (
                page_date
                and record_dt
                and record_dt.date()
                != page_date.date()
            ):

                print(
                    "SKIP DATE MISMATCH:",
                    key,
                    record.get("date")
                )

                continue


            found_this_page += 1
            total_records_seen += 1


            changed = merge_record(
                databases[key],
                record
            )


            if changed:
                total_changes += 1


            print(
                " ",
                key.upper(),
                record["date"],
                record["draw"],
                record["first"],
                record["second"],
                record["third"],
                "S:",
                len(
                    record["special"]
                ),
                "C:",
                len(
                    record["consolation"]
                )
            )


        if found_this_page == 0:

            print(
                "No target-market draw on this date."
            )


        total_pages += 1


        older_url = find_older_url(
            soup,
            current_url
        )


        if not older_url:

            print(
                "No Older link found."
            )

            break


        current_url = older_url


        time.sleep(
            REQUEST_DELAY
        )


    # =====================================================
    # SAVE
    # =====================================================

    print()
    print(
        "========================================"
    )

    print(
        "SAVING DATABASES"
    )

    print(
        "========================================"
    )


    for key, cfg in MARKETS.items():

        database = databases[key]

        clean_database(
            database
        )

        save_json(
            DATA / cfg["file"],
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


    print()
    print(
        "========================================"
    )

    print(
        "UPDATE COMPLETE ✓"
    )

    print(
        "Pages visited:",
        total_pages
    )

    print(
        "Records parsed:",
        total_records_seen
    )

    print(
        "New/changed records:",
        total_changes
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()
