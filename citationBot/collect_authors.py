"""
forge_pc_scraper.py — Extract the FORGE 2026 Research‑Papers Program‑Committee roster
and export it to a CSV file.

Re‑implementation: **structural parsing** with BeautifulSoup selectors replaces the
previous token‑splitting heuristics, so member names of any length are captured
faithfully while affiliation, country, and (optional) role data come straight
from the HTML hierarchy.

Run it as‑is:

    python forge_pc_scraper.py

A file `pc_members.csv` (Name | Role | Affiliation | Country) appears in the
configured `FILES_FOLDER`.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import FILES_FOLDER, CONFERENCE_WEBSITE

# ──────────────────────────────────────────────────────────────────────────────
# 1  Configuration — all hard‑coded on purpose
# ──────────────────────────────────────────────────────────────────────────────
URL: str = CONFERENCE_WEBSITE
OUTPUT: Path = FILES_FOLDER / "pc_members.csv"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}
TIMEOUT_S: int = 30

# ──────────────────────────────────────────────────────────────────────────────
# 2  Fetch page
# ──────────────────────────────────────────────────────────────────────────────
print(f"Downloading → {URL}")
resp = requests.get(URL, headers=HEADERS, timeout=TIMEOUT_S)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

# ──────────────────────────────────────────────────────────────────────────────
# 3  Locate <a> tags that wrap each Program‑Committee member
# ──────────────────────────────────────────────────────────────────────────────
member_links = soup.select('a.navigate[href*="/profile/fse-2026/"]')
print(f"Found {len(member_links)} candidate <a> blocks")

records: list[dict[str, str]] = []
for a in member_links:
    body = a.select_one("div.media-body")
    if body is None:
        continue

    # Name & optional role live in <h3 class="media-heading">Name <small>Role</small></h3>
    name_tag = body.select_one("h3.media-heading")
    if name_tag is None:
        continue

    # First string child (before the <small>) is the author’s name
    name = (name_tag.contents[0].strip() if name_tag.contents else "").replace("\u200b", "")

    # Role lives in the nested <small> tag, default ⇒ "Member"
    role_small = name_tag.select_one("small")
    role = role_small.get_text(strip=True) if role_small and role_small.get_text(strip=True) else "Member"

    # Affiliation in the first <h4> span.text-black
    aff_tag = body.select_one("h4.media-heading span.text-black")
    affiliation = aff_tag.get_text(strip=True) if aff_tag else ""

    # Country in the last <h4> small element
    country_tag = body.select_one("h4.media-heading small:last-of-type")
    country = country_tag.get_text(strip=True) if country_tag else ""

    records.append({
        "Name": name,
        "Role": role,
        "Affiliation": affiliation,
        "Country": country,
    })

# ──────────────────────────────────────────────────────────────────────────────
# 4  Deduplicate entries by name (guards against accidental duplicates)
# ──────────────────────────────────────────────────────────────────────────────
unique: dict[str, dict[str, str]] = {}
for rec in records:
    unique.setdefault(rec["Name"], rec)
records = list(unique.values())
print(f"Parsed {len(records)} unique committee records")

# ──────────────────────────────────────────────────────────────────────────────
# 5  Write CSV
# ──────────────────────────────────────────────────────────────────────────────
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["Name", "Role", "Affiliation", "Country"])
    writer.writeheader()
    writer.writerows(records)

print(f"✅ CSV written → {OUTPUT.resolve()}")

# ──────────────────────────────────────────────────────────────────────────────
# 6  Preview when running interactively
# ──────────────────────────────────────────────────────────────────────────────
if sys.stdout.isatty():
    print("\nPreview (first 10 lines):")
    import itertools

    for rec in itertools.islice(records, 10):
        print(" · ", rec)
