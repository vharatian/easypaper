#!/usr/bin/env python3
"""
build_authors_csv_openalex_by_institution.py

Reads INPUT_PATH with columns: Name, Role, Affiliation, Country.
1) Resolves Affiliation text -> OpenAlex Institution ID via /institutions,
   now sending country_code filter when available.
2) Queries /authors with filter:
     filter=default.search:<name>,last_known_institutions.id:i#########
   (plus per_page, select, sort=relevance_score:desc)
3) Writes ONLY fetched data to OUTPUT_PATH. Source CSV is not modified.

Output columns:
  input_name, author_id, name, url, homepage, hindex, affiliations, confidence
"""

import csv
import os
import time
import unicodedata
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

import requests

from config import FILES_FOLDER

# -------------------- CONFIG --------------------
INPUT_PATH = FILES_FOLDER / Path("pc_members.csv")
OUTPUT_PATH = FILES_FOLDER / Path("authors.csv")

API_BASE = "https://api.openalex.org"
AUTHORS_URL = f"{API_BASE}/authors"
INSTITUTIONS_URL = f"{API_BASE}/institutions"

SELECT_AUTHOR_FIELDS = ",".join([
    "id",
    "display_name",
    "display_name_alternatives",
    "summary_stats",
    "affiliations",
    "last_known_institutions",
    "relevance_score",
    "works_count",
    "cited_by_count",
])

SELECT_INSTITUTION_FIELDS = ",".join([
    "id",
    "display_name",
    "country_code",
    "display_name_acronyms",
    "display_name_alternatives",
    "ror",
    "relevance_score",
])

REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_CALLS = 0.5
MAX_CANDIDATES = 25
MIN_CONFIDENCE = 0.52

OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")  # recommended by OpenAlex
USER_AGENT = f"openalex-author-match/1.0 (+{OPENALEX_MAILTO})" if OPENALEX_MAILTO else "openalex-author-match/1.0"
# ------------------------------------------------

def normalize(s: str) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.lower().strip().split())

def similarity(a: str, b: str) -> float:
    a_n = normalize(a)
    b_n = normalize(b)
    if not a_n or not b_n:
        return 0.0
    return difflib.SequenceMatcher(a=a_n, b=b_n).ratio()

def build_headers() -> Dict[str, str]:
    return {"Accept": "application/json", "User-Agent": USER_AGENT}

def _http_get(url: str, params: Dict[str, Any]) -> requests.Response:
    attempts = 0
    while True:
        attempts += 1
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=build_headers())
            if resp.status_code in (429, 500, 502, 503, 504):
                if attempts < 4:
                    wait = 1.2 * attempts
                    print(f"[warn] HTTP {resp.status_code}; retrying in {wait:.1f}s...")
                    time.sleep(wait)
                    continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempts < 4:
                wait = 1.2 * attempts
                print(f"[warn] {e}; retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise

# -------- Country helpers --------

def map_country_to_iso2(name_or_code: str) -> Optional[str]:
    s = normalize(name_or_code)
    if not s:
        return None
    quick = {
        "united states": "US", "usa": "US",
        "united kingdom": "GB", "uk": "GB",
        "germany": "DE", "deutschland": "DE",
        "switzerland": "CH",
        "canada": "CA",
        "italy": "IT",
        "spain": "ES",
        "france": "FR",
        "netherlands": "NL",
        "austria": "AT",
        "belgium": "BE",
        "sweden": "SE",
        "norway": "NO",
        "denmark": "DK",
        "finland": "FI",
        "ireland": "IE",
        "turkey": "TR",
        "china": "CN",
        "hong kong": "HK",
        "taiwan": "TW",
        "japan": "JP",
        "korea": "KR",
        "india": "IN",
    }
    if len(name_or_code) == 2 and name_or_code.upper().isalpha():
        return name_or_code.upper()
    return quick.get(s)

# -------- Institution resolution (now country-aware) --------

def institution_id_to_filter_val(inst_id: str) -> Optional[str]:
    """https://openalex.org/I204722609 -> i204722609"""
    if not inst_id:
        return None
    short = inst_id.rsplit("/", 1)[-1]
    if not short or (short[0] not in ("I", "i")):
        return None
    digits = short[1:]
    if not digits.isdigit():
        return None
    return "i" + digits

_inst_cache: Dict[Tuple[str, str], Optional[str]] = {}

def score_institution(cand: Dict[str, Any], target_affiliation: str, target_country_iso2: str) -> float:
    score = 0.0
    dn = cand.get("display_name") or ""
    aliases = (cand.get("display_name_alternatives") or []) + (cand.get("display_name_acronyms") or [])
    ccode = (cand.get("country_code") or "").upper()

    # Name/alias similarity
    score += 0.70 * similarity(dn, target_affiliation)
    for al in aliases:
        score = max(score, 0.70 * similarity(al, target_affiliation))

    # Country nudge
    if target_country_iso2 and target_country_iso2 == ccode:
        score += 0.12

    # Relevance score nudge if present
    if "relevance_score" in cand and isinstance(cand["relevance_score"], (int, float)):
        score += min(0.12, 0.03 * float(cand["relevance_score"]))

    return min(score, 1.0)

def resolve_institution_id(affiliation: str, country: str) -> Optional[str]:
    """
    Resolve affiliation -> OpenAlex institution ID.
    Now includes a country_code filter when available to disambiguate multi-country orgs (e.g., Huawei).
    Strategy:
      A) search=<affiliation>, filter=country_code:<ISO2>
      B) if A empty -> search=<affiliation> (no filter)
    Returns canonical ID (e.g., 'https://openalex.org/I204722609') or None.
    """
    aff_norm = normalize(affiliation)
    if not aff_norm:
        return None

    iso = map_country_to_iso2(country or "")
    cache_key = (aff_norm, iso or "")
    if cache_key in _inst_cache:
        return _inst_cache[cache_key]

    attempts: List[Dict[str, Any]] = []

    # A) Country-constrained search
    if iso:
        attempts.append({
            "search": affiliation,
            "per_page": 25,
            "select": SELECT_INSTITUTION_FIELDS,
            "filter": f"country_code:{iso}",
        })

    # B) Fallback: no country filter
    attempts.append({
        "search": affiliation,
        "per_page": 25,
        "select": SELECT_INSTITUTION_FIELDS,
    })

    for idx, params in enumerate(attempts, 1):
        if OPENALEX_MAILTO:
            params["mailto"] = OPENALEX_MAILTO
        try:
            resp = _http_get(INSTITUTIONS_URL, params)
            data = resp.json() or {}
            results = data.get("results", []) or []
            if not results:
                continue

            # Pick best by scoring (country-aware)
            best_id = None
            best_score = -1.0
            for r in results:
                sc = score_institution(r, affiliation, iso or "")
                if sc > best_score:
                    best_score = sc
                    best_id = r.get("id")

            if best_id and best_score >= 0.45:
                _inst_cache[cache_key] = best_id
                return best_id
        except Exception as e:
            print(f"[warn] institution attempt {idx} failed: {e}")
            continue

    _inst_cache[cache_key] = None
    return None

# -------- Author search & scoring --------

def extract_aff_text(cand: Dict[str, Any]) -> str:
    texts: List[str] = []
    lkis = cand.get("last_known_institutions") or []
    if isinstance(lkis, list):
        for inst in lkis:
            dn = (inst or {}).get("display_name") or ""
            if dn:
                texts.append(dn)
    if not texts:
        affs = cand.get("affiliations") or []
        if isinstance(affs, list):
            texts.extend([a for a in affs if isinstance(a, str)])
        elif isinstance(affs, str):
            texts.append(affs)

    seen: Set[str] = set()
    uniq = []
    for t in texts:
        t_norm = t.strip()
        if t_norm and t_norm not in seen:
            seen.add(t_norm)
            uniq.append(t_norm)
    return " ; ".join(uniq)

def openalex_country_codes(cand: Dict[str, Any]) -> Set[str]:
    codes: Set[str] = set()
    lkis = cand.get("last_known_institutions") or []
    if isinstance(lkis, list):
        for inst in lkis:
            cc = (inst or {}).get("country_code")
            if cc:
                codes.add(str(cc).upper())
    return codes

def score_candidate(candidate: Dict[str, Any], target_name: str, target_affiliation: str, target_country: str) -> float:
    score = 0.0
    cand_name = candidate.get("display_name", "") or ""
    aliases = candidate.get("display_name_alternatives", []) or []
    cand_aff_text = extract_aff_text(candidate)
    cand_ccodes = openalex_country_codes(candidate)

    if normalize(cand_name) == normalize(target_name):
        score += 0.62
    else:
        score += 0.40 * similarity(cand_name, target_name)

    for alias in aliases:
        if normalize(alias) == normalize(target_name):
            score += 0.30
            break

    if target_affiliation:
        score += 0.38 * similarity(cand_aff_text, target_affiliation)

    if target_country:
        tc = map_country_to_iso2(target_country)
        if tc and tc in cand_ccodes:
            score += 0.06
        elif normalize(target_country) in normalize(cand_aff_text):
            score += 0.04

    return min(score, 1.0)

def choose_best_candidate(candidates: List[Dict[str, Any]], name: str, affiliation: str, country: str) -> Optional[Dict[str, Any]]:
    best = None
    best_score = -1.0
    for c in candidates:
        sc = score_candidate(c, name, affiliation, country)
        if sc > best_score:
            best_score = sc
            best = (c, sc)
    if best and best[1] >= MIN_CONFIDENCE:
        return {"candidate": best[0], "confidence": round(best[1], 3)}
    return None

def oa_id_to_short(openalex_id: str) -> str:
    if not openalex_id:
        return ""
    return openalex_id.rsplit("/", 1)[-1]

def author_search_with_institution(name: str, inst_filter_id: str, per_page: int = MAX_CANDIDATES) -> List[Dict[str, Any]]:
    params = {
        "filter": f"default.search:{name},last_known_institutions.id:{inst_filter_id}",
        "sort": "relevance_score:desc",
        "per_page": per_page,
        "select": SELECT_AUTHOR_FIELDS,
    }
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    resp = _http_get(AUTHORS_URL, params)
    data = resp.json() or {}
    return data.get("results", []) or []

def fallback_author_search(name: str, affiliation: str, per_page: int = MAX_CANDIDATES) -> List[Dict[str, Any]]:
    attempts = [
        {"search": f"{name} {affiliation}".strip()},
        {"search": name},
    ]
    for params in attempts:
        params.update({"per_page": per_page, "select": SELECT_AUTHOR_FIELDS})
        if OPENALEX_MAILTO:
            params["mailto"] = OPENALEX_MAILTO
        try:
            resp = _http_get(AUTHORS_URL, params)
            data = resp.json() or {}
            results = data.get("results", []) or []
            if results:
                return results
        except Exception as e:
            print(f"[warn] fallback author search failed: {e}")
            continue
    return []

# ---------------- Main ----------------

def process_csv(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"CSV not found: {input_path}")

    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    out_fields = [
        "input_name",
        "author_id",
        "name",
        "url",
        "homepage",
        "hindex",
        "affiliations",
        "confidence",
    ]

    matches_written = 0
    with output_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=out_fields)
        writer.writeheader()

        for i, row in enumerate(rows, start=1):
            name = (row.get("Name") or "").strip()
            aff = (row.get("Affiliation") or "").strip()
            country = (row.get("Country") or "").strip()

            if not name:
                print(f"[warn] Row {i}: missing Name; skipping.")
                continue

            print(f"[{i}/{len(rows)}] Resolving institution for: {name} | Affil: {aff or '-'} | Country: {country or '-'}")
            inst_id_full = resolve_institution_id(aff, country) if aff else None
            inst_filter_val = institution_id_to_filter_val(inst_id_full) if inst_id_full else None

            try:
                if inst_filter_val:
                    print(f"   -> using institution filter: {inst_filter_val}")
                    candidates = author_search_with_institution(name, inst_filter_val, per_page=MAX_CANDIDATES)
                else:
                    candidates = fallback_author_search(name, aff, per_page=MAX_CANDIDATES)
            except Exception as e:
                print(f"[error] author search failed for '{name}': {e}")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            if not candidates:
                print("   -> no candidates found")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            match = choose_best_candidate(candidates, name, aff, country)
            if not match:
                print("   -> no confident match")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            c = match["candidate"]
            oa_id_full = c.get("id", "") or ""
            oa_id_short = oa_id_to_short(oa_id_full)
            disp_name = c.get("display_name") or ""
            aff_text = extract_aff_text(c)

            hindex = ""
            ss = c.get("summary_stats") or {}
            if isinstance(ss, dict):
                hindex = ss.get("h_index", "")

            out_row = {
                "input_name": name,
                "author_id": oa_id_short,
                "name": disp_name,
                "url": oa_id_full,
                "homepage": "",
                "hindex": hindex,
                "affiliations": aff_text,
                "confidence": match["confidence"],
            }
            writer.writerow(out_row)
            matches_written += 1
            print(f"   -> matched OpenAlex {oa_id_short} (confidence={match['confidence']})")

            time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"[done] Wrote {matches_written} matched authors to: {output_path}")

if __name__ == "__main__":
    process_csv(INPUT_PATH, OUTPUT_PATH)
