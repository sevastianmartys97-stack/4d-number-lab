from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "cashsweep.json"

START_DATE = "2021-01-01"
END_DATE = "2026-12-31"

START_URL = (
    "https://www.4d2u.com.my/"
    "result.php?drawid=4400%2F21&lang=E&source=W"
)

MAX_PAGES = 1200
REQUEST_TIMEOUT = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131 Safari/537.36"
    )
}


def normalize4(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits:
        return ""
    return digits[-4:].zfill(4)


def normalize_date(value):
    value = str(value or "").strip()

    for fmt in (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def load_existing():
    if not DATA_FILE.exists():
        return {
            "market": "Cash Sweep",
            "draws": []
        }

    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_database(database):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(database, f, indent=2, ensure_ascii=False)
        f.write("\n")


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_numbers(text):
    return re.findall(r"(?<!\d)\d{4}(?!\d)", text)


def find_date(text):
    match = re.search(
        r"Date\s+(\d{2}/\d{2}/\d{4})",
        text,
        re.I
    )

    if not match:
        return ""

    return normalize_date(match.group(1))


def find_draw_id(text):
    match = re.search(
        r"DrawID\s*#?\s*([0-9]+(?:/[0-9]+)?)",
        text,
        re.I
    )

    if not match:
        return ""

    return match.group(1)


def extract_section(text, start_label, end_label=None):
    low = text.lower()

    start = low.find(start_label.lower())

    if start == -1:
        return ""

    start += len(start_label)

    if end_label:
        end = low.find(
            end_label.lower(),
            start
        )

        if end != -1:
            return text[start:end]

    return text[start:]


def parse_result(html):
    soup = BeautifulSoup(html, "html.parser")

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

    text = clean_text(text)

    if "Cash Sweep" not in text:
        return None

    date_value = find_date(text)

    if not date_value:
        return None

    draw_id = find_draw_id(text)

    # ------------------------------------------------
    # Top 3
    # Find 4-digit First/Second/Third section.
    # ------------------------------------------------

    top_match = re.search(
        r"First Prize\s+Second Prize\s+Third Prize"
        r".*?"
        r"First Prize\s+Second Prize\s+Third Prize\s+"
        r"(\d{4})\s+(\d{4})\s+(\d{4})",
        text,
        re.I
    )

    if not top_match:
        return None

    first = normalize4(top_match.group(1))
    second = normalize4(top_match.group(2))
    third = normalize4(top_match.group(3))

    # ------------------------------------------------
    # Special
    # ------------------------------------------------

    special_text = extract_section(
        text,
        "Special Prize",
        "Consolation Prize"
    )

    special = extract_numbers(
        special_text
    )[:10]

    # ------------------------------------------------
    # Consolation
    # ------------------------------------------------

    consolation_text = extract_section(
        text,
        "Consolation Prize",
        "Other sources"
    )

    consolation = extract_numbers(
        consolation_text
    )[:10]

    if len(special) < 10:
        return None

    if len(consolation) < 10:
        return None

    return {
        "draw": draw_id,
        "date": date_value,
        "first": first,
        "second": second,
        "third": third,
        "special": special,
        "consolation": consolation
    }


def find_next_url(html, current_url):
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        label = clean_text(
            a.get_text(" ", strip=True)
        ).lower()

        if "next draw" not in label:
            continue

        href = a.get("href", "")

        if not href:
            continue

        return urljoin(
            current_url,
            href
        )

    return ""


def record_score(record):
    score = 0

    if record.get("first"):
        score += 10

    if record.get("second"):
        score += 10

    if record.get("third"):
        score += 10

    score += len(
        record.get("special", [])
    )

    score += len(
        record.get("consolation", [])
    )

    return score


def merge_existing(records):
    existing = load_existing()

    by_date = {}

    for old in existing.get("draws", []):
        if not isinstance(old, dict):
            continue

        date_value = normalize_date(
            old.get("date")
        )

        if not date_value:
            continue

        if date_value < START_DATE:
            continue

        if date_value > END_DATE:
            continue

        cleaned = {
            "draw": str(old.get("draw", "")),
            "date": date_value,
            "first": normalize4(old.get("first")),
            "second": normalize4(old.get("second")),
            "third": normalize4(old.get("third")),
            "special": [
                normalize4(x)
                for x in old.get("special", [])
                if normalize4(x)
            ],
            "consolation": [
                normalize4(x)
                for x in old.get("consolation", [])
                if normalize4(x)
            ]
        }

        if not (
            cleaned["first"]
            and cleaned["second"]
            and cleaned["third"]
        ):
            continue

        by_date[date_value] = cleaned

    for record in records:
        date_value = record["date"]

        current = by_date.get(date_value)

        if (
            current is None
            or record_score(record)
            >= record_score(current)
        ):
            by_date[date_value] = record

    output = list(by_date.values())

    output.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    return output


def main():
    print("=" * 65)
    print("CASH SWEEP HISTORY BUILDER")
    print("2021 -> 2026")
    print("=" * 65)

    session = requests.Session()

    current_url = START_URL

    scanned = 0
    parsed = 0
    records = []

    visited = set()

    while current_url:
        if current_url in visited:
            print("Duplicate URL detected, stopping.")
            break

        visited.add(current_url)

        scanned += 1

        if scanned > MAX_PAGES:
            print("MAX_PAGES reached.")
            break

        try:
            response = session.get(
                current_url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

        except Exception as e:
            print("Request failed:", e)
            break

        record = parse_result(
            response.text
        )

        if record:
            date_value = record["date"]

            if START_DATE <= date_value <= END_DATE:
                records.append(record)
                parsed += 1

                print(
                    "✓",
                    record["date"],
                    record["draw"],
                    record["first"],
                    record["second"],
                    record["third"]
                )

            if date_value > END_DATE:
                break

        next_url = find_next_url(
            response.text,
            current_url
        )

        if not next_url:
            print("No Next Draw link found.")
            break

        current_url = next_url

        # Very small delay.
        # This is one-time history build,
        # not a daily scanner.
        time.sleep(0.03)

    draws = merge_existing(
        records
    )

    if draws:
        newest = draws[0]["date"]
        oldest = draws[-1]["date"]
    else:
        newest = ""
        oldest = ""

    database = {
        "market": "Cash Sweep",

        "lastUpdated": newest,

        "historyCoverage": {
            "drawCount": len(draws),
            "oldestDate": oldest,
            "newestDate": newest
        },

        "historyRange": {
            "from": START_DATE,
            "to": END_DATE
        },

        "historySource":
            "4D2U historical Cash Sweep archive + existing records",

        "draws": draws
    }

    print()
    print("=" * 65)
    print("FINAL")
    print("=" * 65)

    print("Pages scanned :", scanned)
    print("Records parsed:", parsed)
    print("Total draws   :", len(draws))
    print("Oldest        :", oldest)
    print("Newest        :", newest)

    if len(draws) < 500:
        raise RuntimeError(
            "Cash Sweep history looks incomplete: "
            f"only {len(draws)} draws."
        )

    if not oldest or oldest > "2021-12-31":
        raise RuntimeError(
            "Cash Sweep did not reach 2021."
        )

    save_database(
        database
    )

    print()
    print("CASH SWEEP DATABASE SUCCESS ✓")
    print("=" * 65)


if __name__ == "__main__":
    main()
