#!/usr/bin/env python3
"""
openalex_author_works_to_csv.py

Input CSV format (must include these columns at minimum):
    Name,author_id
    Alice Smith,A123456789
    ...

For each author, creates: ./out/<author-kebab>.csv with columns:
    title,year,citation_count,conference_link,pdf_link,abstract

- Uses the OpenAlex Works API with cursor pagination
- Streams rows to disk as they are fetched (no waiting for the end)
- Shows progress bars for authors and for each author's papers via tqdm
- Includes exponential backoff & retry for transient errors
"""

import csv
import os
import re
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm

from config import FILES_FOLDER

# --------------------- CONFIG (edit these) ---------------------
INPUT_CSV = FILES_FOLDER / Path("authors.csv")        # your input file: must have columns Name,author_id
OUTPUT_DIR = FILES_FOLDER / Path("alex_papers")               # where per-author CSVs will be written
OPENALEX_BASE = "https://api.openalex.org/works"
PER_PAGE = 200                         # max allowed by OpenAlex
YEAR_MIN: Optional[int] = None         # e.g., 2015 to limit by year, or None for all years
REQUESTS_PER_SECOND = 5                # be polite; OpenAlex allows reasonable rates
MAILTO = "you@example.com"             # set your email for OpenAlex polite usage
# ---------------------------------------------------------------


def slugify(name: str) -> str:
    """Convert a human name to a safe kebab-case filename."""
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)     # drop punctuation
    s = re.sub(r"\s+", "-", s)         # spaces -> dashes
    s = re.sub(r"-+", "-", s)          # collapse dashes
    return s or "author"


def build_session() -> requests.Session:
    """HTTP session with retry/backoff."""
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": f"openalex-fetch/1.0 ({MAILTO})"})
    return s


def reconstruct_abstract(inv_idx: Optional[Dict[str, Iterable[int]]]) -> str:
    """
    OpenAlex returns abstract_inverted_index: {word: [positions...], ...}
    Rebuild a readable abstract string from it.
    """
    if not inv_idx:
        return ""
    # Determine total length: highest position + 1
    max_pos = -1
    for positions in inv_idx.values():
        for p in positions:
            if p > max_pos:
                max_pos = p
    words = [""] * (max_pos + 1)
    for word, positions in inv_idx.items():
        for p in positions:
            words[p] = word
    # Clean up multiple spaces just in case
    abstract = " ".join(w for w in words if w is not None)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    return abstract


def pick_links(work: Dict) -> Tuple[str, str]:
    """
    Derive (conference_link, pdf_link) from a work record.
    Strategy:
      - conference_link: prefer primary_location.landing_page_url, else host_venue.url, else doi
      - pdf_link: prefer best_oa_location.pdf_url, else primary_location.pdf_url
    """
    doi_url = f"https://doi.org/{work.get('doi')}" if work.get("doi") else ""

    primary = work.get("primary_location") or {}
    host_venue = work.get("host_venue") or {}
    best_oa = work.get("best_oa_location") or {}

    conference_link = (
        primary.get("landing_page_url")
        or host_venue.get("url")
        or doi_url
        or ""
    )
    pdf_link = (
        best_oa.get("pdf_url")
        or primary.get("pdf_url")
        or ""
    )
    return conference_link or "", pdf_link or ""


def rate_limit(last_call_time: list):
    """
    Simple client-side rate limit to ~REQUESTS_PER_SECOND.
    last_call_time is a single-item list with the timestamp of the last call.
    """
    min_interval = 1.0 / max(1, REQUESTS_PER_SECOND)
    now = time.time()
    elapsed = now - last_call_time[0]
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    last_call_time[0] = time.time()


def fetch_author_works(session: requests.Session, author_id: str) -> Iterable[Dict]:
    """
    Yield all works for an author using cursor pagination.
    Applies YEAR_MIN filter if set.
    """
    params = {
        "filter": f"author.id:{author_id}",
        "per_page": PER_PAGE,
        "cursor": "*",
        "sort": "publication_year:desc",
    }
    if YEAR_MIN:
        params["filter"] += f",from_publication_date:{YEAR_MIN}-01-01"

    last_call = [0.0]
    total_known = None  # from meta.count

    with tqdm(total=0, unit="paper", leave=False, desc="papers", disable=True) as _:
        # We don't use this outer tqdm; we’ll return items to let caller manage the tqdm with known total.
        pass

    while True:
        rate_limit(last_call)
        r = session.get(OPENALEX_BASE, params=params, timeout=30)
        if r.status_code >= 400:
            # Let the retry adapter handle most; if still bad, raise for clarity
            r.raise_for_status()
        data = r.json()
        if total_known is None:
            total_known = (data.get("meta") or {}).get("count") or 0

        for work in data.get("results", []):
            yield work

        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor


def write_author_csv(session: requests.Session, author_name: str, author_id: str):
    """Stream an author's works into a CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{slugify(author_name)}.csv"

    # First request just to get total count for a nice tqdm
    probe_params = {
        "filter": f"author.id:{author_id}" + (f",from_publication_date:{YEAR_MIN}-01-01" if YEAR_MIN else ""),
        "per_page": 1,
        "cursor": "*",
    }
    r = session.get(OPENALEX_BASE, params=probe_params, timeout=30)
    if r.status_code >= 400:
        r.raise_for_status()
    total = (r.json().get("meta") or {}).get("count") or 0

    # Now iterate with the real generator
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "year", "citation_count", "conference_link", "pdf_link", "abstract"])

        for work in fetch_author_works(session, author_id):
            title = (work.get("title") or "").replace("\n", " ").strip()
            year = work.get("publication_year") or ""
            cited = work.get("cited_by_count") or 0
            conference_link, pdf_link = pick_links(work)
            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

            writer.writerow([title, year, cited, conference_link, pdf_link, abstract])


def read_authors(input_csv: Path) -> Iterable[Tuple[str, str]]:
    """Yield (Name, author_id) from the input CSV, skipping malformed rows."""
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"name", "author_id"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Input CSV missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            name = (row.get("name") or "").strip()
            aid = (row.get("author_id") or "").strip()
            if not name or not aid:
                continue
            yield name, aid


def main():
    session = build_session()
    authors = list(read_authors(INPUT_CSV))

    if not authors:
        print("No authors found in the input CSV.")
        return

    with tqdm(total=len(authors), unit="author", desc="Authors") as authors_bar:
        for name, aid in authors:
            try:
                write_author_csv(session, name, aid)
            except Exception as e:
                # Log and continue with next author
                tqdm.write(f"[WARN] Failed for {name} ({aid}): {e}")
            finally:
                authors_bar.update(1)


if __name__ == "__main__":
    main()
