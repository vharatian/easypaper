#!/usr/bin/env python3
"""
Find potential citation candidates by abstract similarity.

- Scans a folder of CSV files that contain paper metadata (title, abstract, etc.).
- Embeds ONLY the abstracts and computes cosine similarity to a hardcoded query abstract.
- Produces a single CSV ranked by similarity: query_title, query_abstract, candidate_title, candidate_abstract, source_csv, similarity, rank.

Notes:
- The script prefers Sentence-Transformers ("all-MiniLM-L6-v2") if installed.
- Otherwise it falls back to TF-IDF + cosine similarity.
- No CLI args; everything is hardcoded below.
"""

import os
import sys
import glob
import math
import csv
from pathlib import Path
from typing import List, Tuple
import pandas as pd
import numpy as np

from config import FILES_FOLDER, PAPER_TITLE, PAPER_ABSTRACT, NUM_RELEVANT_PAPERS

# -------------------------- HARD-CODED SETTINGS --------------------------
INPUT_DIR = FILES_FOLDER / "alex_papers"       # <-- change this
OUTPUT_CSV = FILES_FOLDER / "citation_candidates.csv"  # <-- change this
# If your CSVs have different column names, add them above.

# Your query paper (the one we're trying to find citations for)
# Imported from config.py
QUERY_TITLE = PAPER_TITLE
QUERY_ABSTRACT = PAPER_ABSTRACT

# How many top candidates to export
TOP_K = NUM_RELEVANT_PAPERS

# Deduplication heuristics
DROP_DUPLICATES_BY_TITLE = True
CASE_INSENSITIVE_DEDUP   = True

# ------------------------------------------------------------------------


def _pick_first_present_column(df: pd.DataFrame, candidates: List[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    return ""


def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    # keep it simple: lowercase; avoid heavy cleaning to preserve signal
    return s.lower()


def _load_all_papers(input_dir: Path) -> pd.DataFrame:
    rows = []
    for path in glob.glob(str(input_dir / "*.csv")):
        try:
            df = pd.read_csv(path, dtype=str, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            # fallback with errors='ignore'
            df = pd.read_csv(path, dtype=str, encoding_errors="ignore", on_bad_lines="skip")

        sub = df[["title", "abstract"]]
        sub["source_csv"] = os.path.basename(path)
        rows.append(sub)

    if not rows:
        return pd.DataFrame(columns=["title", "abstract", "source_csv"])

    all_df = pd.concat(rows, ignore_index=True)
    # Normalize fields
    all_df["title"] = all_df["title"].fillna("").astype(str)
    all_df["abstract"] = all_df["abstract"].fillna("").astype(str)

    if DROP_DUPLICATES_BY_TITLE:
        if CASE_INSENSITIVE_DEDUP:
            all_df["_title_norm"] = all_df["title"].str.lower().str.strip()
            all_df = all_df.drop_duplicates(subset=["_title_norm"]).drop(columns=["_title_norm"])
        else:
            all_df = all_df.drop_duplicates(subset=["title"])

    # Drop rows with empty abstracts (we compare by abstract only)
    all_df = all_df[all_df["abstract"].str.strip().ne("")]
    all_df = all_df.reset_index(drop=True)
    return all_df


def _tfidf_embed_and_score(query_abs: str, abstracts: List[str]) -> np.ndarray:
    """
    Returns cosine similarity scores using TF-IDF.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    corpus = [query_abs] + abstracts
    vec = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9,
        strip_accents="unicode"
    )
    X = vec.fit_transform(corpus)
    sims = cosine_similarity(X[0:1], X[1:]).flatten()
    return sims


def _st_embed_and_score(query_abs: str, abstracts: List[str]) -> np.ndarray:
    """
    Returns cosine similarity scores using Sentence-Transformers (if available).
    """
    # raise RuntimeError("Sentence-Transformers not available")
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception as e:
        raise RuntimeError("Sentence-Transformers not available") from e

    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    emb_q = model.encode([query_abs], normalize_embeddings=True)
    emb_c = model.encode(
        abstracts,
        normalize_embeddings=True,
        show_progress_bar=True,  # ← progress bar for emb_c
        batch_size=16,
        convert_to_numpy=True,
    )
    sims = (emb_q @ emb_c.T).flatten()  # cosine because normalized
    return sims


def _score_candidates(query_abs: str, df: pd.DataFrame) -> np.ndarray:
    abstracts = df["abstract"].astype(str).tolist()

    # Prefer ST if available; otherwise TF-IDF
    try:
        sims = _st_embed_and_score(query_abs, abstracts)
        backend = "sentence-transformers"
    except Exception:
        sims = _tfidf_embed_and_score(query_abs, abstracts)
        backend = "tfidf"
    print(f"[info] Embedding backend: {backend} | Compared {len(abstracts)} abstracts.")
    return sims


def main():
    os.makedirs(OUTPUT_CSV.parent, exist_ok=True)

    # Load all papers from CSVs
    papers = _load_all_papers(INPUT_DIR)
    if papers.empty:
        print(f"[error] No valid CSVs found in {INPUT_DIR} with required columns.")
        sys.exit(1)

    # Compute similarity using abstracts only
    query_abs_norm = _normalize_text(QUERY_ABSTRACT)
    cand_abs_norm = papers["abstract"].apply(_normalize_text).tolist()
    sims = _score_candidates(query_abs_norm, papers.assign(abstract=cand_abs_norm))

    # Rank and prepare output
    papers = papers.copy()
    papers["similarity"] = sims

    # If an identical abstract exists (same as query), push it down or remove
    # (We keep it but it's naturally ranked; adjust here if needed.)

    papers = papers.sort_values("similarity", ascending=False).reset_index(drop=True)
    if TOP_K is not None and TOP_K > 0:
        papers = papers.head(TOP_K).copy()
    papers["rank"] = np.arange(1, len(papers) + 1)

    # Prepare final result CSV
    out_cols = [
        "query_title",
        "query_abstract",
        "candidate_title",
        "candidate_abstract",
        "source_csv",
        "similarity",
        "rank",
    ]

    out_df = pd.DataFrame({
        "candidate_title": papers["title"].tolist(),
        "candidate_abstract": papers["abstract"].tolist(),
        "source_csv": papers["source_csv"].tolist(),
        "similarity": papers["similarity"].round(6).tolist(),
        "rank": papers["rank"].tolist(),
    })

    # Write CSV (UTF-8, no index)
    out_df.to_csv(OUTPUT_CSV, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"[ok] Wrote {len(out_df)} candidates to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
