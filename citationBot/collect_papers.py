#!/usr/bin/env python3
"""
scrape_2015.py  – two-phase, streaming CSV write
  1) collect candidate pubs (cheap)
  2) enrich each pub, append row to its author's CSV on the fly
"""

from __future__ import annotations

import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from scholarly import scholarly                    #  pip install scholarly
from tqdm.auto import tqdm                         #  pip install tqdm

from config import FILES_FOLDER

# ─────────────────── user settings ───────────────────
INPUT_FILE   = FILES_FOLDER / "profiles.txt"
OUTPUT_DIR   = FILES_FOLDER / "papers"
YEAR_FILTER  = 2015          # keep > YEAR_FILTER  (i.e. 2016+)
WAIT_SECS    = 5             # polite pause between fill() calls
MAX_RETRIES  = 3
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# ─────────────────────────────────────────────────────


def kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ───────── helper API wrappers ─────────
def fetch_profile(url: str):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return scholarly.search_author_id(url)
        except Exception as e:                       # noqa: BLE001
            tqdm.write(f"[warn] {url}  ({attempt}/{MAX_RETRIES})  {e}")
            time.sleep(WAIT_SECS)
    raise RuntimeError(f"failed to fetch profile after {MAX_RETRIES} tries: {url}")


def collect_candidate_pubs(profile) -> List[dict]:
    """Return *minimal* pub dicts (cheap, no full fill)."""
    out = []
    filled = scholarly.fill(profile, sections=["publications"])
    for pub in filled["publications"]:
        bib = pub.get("bib", {})
        try:
            yr = int(bib.get("pub_year") or bib.get("year") or 0)
        except ValueError:
            continue
        if yr > YEAR_FILTER:
            out.append({"pub": pub, "year": yr})
    return out


def enrich(pub_entry: dict) -> dict:
    """Full fill(); return row ready for csv."""
    full = scholarly.fill(pub_entry["pub"])
    bib  = full.get("bib", {})
    title    = (bib.get("title","")    .replace("\n"," ").strip())
    abstract = (bib.get("abstract","").replace("\n"," ").strip())
    cites    = full.get("num_citations", 0)

    # ─── NEW: collect candidate links ───
    links: List[str] = []
    for key in ("eprint_url", "pub_url"):
        link = full.get(key)
        if link:
            links.append(link)

    pdf_link, conf_link = "", ""
    for link in links:
        if link.lower().endswith(".pdf") or "pdf" in link.lower():
            pdf_link = pdf_link or link  # keep first pdf
        else:
            conf_link = conf_link or link

    return {
        "title": title,
        "year": int(pub_entry.get("pub_year") or pub_entry.get("year") or 0),
        "citation_count": cites,
        "conference_link": conf_link,
        "pdf_link": pdf_link,
        "abstract": abstract,

    }


# ───────── main routine ─────────
def main() -> None:
    urls = [u.strip() for u in Path(INPUT_FILE).read_text().splitlines() if u.strip()]
    if not urls:
        sys.exit("[error] profiles.txt is empty")

    # —— Phase 1: harvest candidates ——
    pubs_by_author: Dict[str, List[dict]] = defaultdict(list)
    profiles_by_author = {}                       # kebab → profile object

    for url in tqdm(urls, desc="Collecting authors", unit="author"):
        profile = fetch_profile(url)
        kname   = kebab(profile.get("name", "unknown"))
        profiles_by_author[kname] = profile
        pubs_by_author[kname].extend(collect_candidate_pubs(profile))

    total_papers = sum(len(lst) for lst in pubs_by_author.values())
    if not total_papers:
        sys.exit(f"[info] no pubs later than {YEAR_FILTER}")

    # —— Phase 2: enrich + stream-write rows ——
    bar = tqdm(total=total_papers, desc="Papers", unit="paper")
    for kname, entries in pubs_by_author.items():
        out_path = OUTPUT_DIR / f"{kname}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "title",
                    "year",
                    "citation_count",
                    "conference_link",
                    "pdf_link",
                    "abstract",
                ],
            )
            writer.writeheader()

            for idx, entry in enumerate(entries, start=1):
                row = enrich(entry)
                writer.writerow(row)
                fh.flush()                        # ensure row is on disk immediately
                bar.update(1)
                bar.set_postfix_str(f"{kname}  ({idx}/{len(entries)})")
                time.sleep(WAIT_SECS)             # be polite

        tqdm.write(f"[done] {kname}: {len(entries)} rows → {out_path}")

    bar.close()


if __name__ == "__main__":
    main()
