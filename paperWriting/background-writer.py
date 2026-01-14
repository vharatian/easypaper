#!/usr/bin/env python3
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from tqdm import tqdm
import google.generativeai as genai


# -------------------- small helpers --------------------
def read_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def read_text(p: Path) -> str:
    with p.open("r", encoding="utf-8") as f:
        return f.read()

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def sanitize(name: str, max_len: int = 80) -> str:
    s = re.sub(r"\s+", "_", name.lower().strip())
    s = re.sub(r"[^a-z0-9._-]", "", s)
    return s[:max_len]

def list_files_by_ids(papers_dir: Path, ids: List[str]) -> Dict[str, List[Path]]:
    out = {pid: [] for pid in ids}
    files = [f for f in papers_dir.iterdir() if f.is_file()]
    for pid in ids:
        pat = re.compile(rf"^{re.escape(pid)}[.\s_-].*", re.IGNORECASE)
        for f in files:
            if pat.match(f.name):
                out[pid].append(f)
    return out

def split_json_vs_others(paths: List[Path]) -> Tuple[List[Path], List[Path]]:
    jsons, others = [], []
    for p in paths:
        if p.suffix.lower() == ".json":
            jsons.append(p)
        else:
            others.append(p)
    return jsons, others

def load_and_merge_json_files(json_files: List[Path]) -> List[dict]:
    merged = []
    for fp in json_files:
        try:
            data = read_json(fp)
            if isinstance(data, list):
                merged.extend(data)
            elif isinstance(data, dict):
                merged.append(data)
            else:
                tqdm.write(f"[warn] {fp.name} is not list/dict, skipping")
        except Exception as e:
            tqdm.write(f"[warn] failed to read {fp.name}: {e}")
    return merged

def upload_non_json(files: List[Path]) -> List:
    out = []
    for fp in files:
        try:
            out.append(genai.upload_file(path=str(fp)))
        except Exception as e:
            tqdm.write(f"[warn] upload failed {fp.name}: {e}")
    return out

def send_with_retries(model, contents, retries: int = 3, backoff: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            return model.generate_content(contents)
        except Exception as e:
            if attempt == retries:
                raise
            sleep_for = backoff ** attempt
            tqdm.write(f"[retry] {e} – {sleep_for:.1f}s")
            time.sleep(sleep_for)

def build_prompt(base_prompt: str, category_obj: dict, merged_json_payload: List[dict]) -> str:
    lines = []
    lines.append(base_prompt.strip())
    lines.append("\n% -------- Assistant-visible Context --------")
    lines.append(f"% Category: {category_obj.get('category_name','')}")
    lines.append("% Papers (id :: title):")
    for p in category_obj.get("papers", []):
        lines.append(f"%   {p.get('id','?')} :: {p.get('title','?')}")
    lines.append("% JSON payload for the papers in this category (do not output verbatim; synthesize):")
    try:
        payload_str = json.dumps(merged_json_payload, ensure_ascii=False, indent=2)
    except Exception:
        payload_str = "[]"
    # keep JSON inline (no fences) so the model can parse easily
    lines.append(payload_str)
    lines.append("% -------- End Context --------\n")
    return "\n".join(lines)


# -------------------- core pipeline --------------------
def run_generation(
    json_path: Path,
    prompt_path: Path,
    papers_dir: Path,
    output_dir: Path,
    model_name: str,
    max_categories: int | None = None,
):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY missing in environment or .env")

    genai.configure(api_key=api_key)
    ensure_dir(output_dir)

    categories = read_json(json_path)
    if max_categories is not None:
        categories = categories[:max_categories]

    base_prompt = read_text(prompt_path)
    model = genai.GenerativeModel(model_name)

    pbar = tqdm(total=len(categories), desc="Categories", unit="cat")
    for idx, cat in enumerate(categories, 1):
        cat_name = cat.get("category_name", f"category_{idx}")
        ids = [p.get("id", "").strip() for p in cat.get("papers", []) if p.get("id")]

        id2files = list_files_by_ids(papers_dir, ids)
        all_files = [fp for lst in id2files.values() for fp in lst]
        json_files, other_files = split_json_vs_others(all_files)

        merged_json = load_and_merge_json_files(json_files)  # <- embed into prompt
        prompt_for_cat = build_prompt(base_prompt, cat, merged_json)

        uploads = upload_non_json(other_files)  # PDFs, TXTs, etc. (JSONs are NOT uploaded)
        contents = [prompt_for_cat] + uploads

        try:
            resp = send_with_retries(model, contents)
            text = (resp.text or "").strip()
        except Exception as e:
            tqdm.write(f"[error] generation failed for '{cat_name}': {e}")
            pbar.update(1)
            continue

        if not text:
            tqdm.write(f"[warn] empty response for '{cat_name}'")
            pbar.update(1)
            continue

        out_path = output_dir / f"{idx:02d}_{sanitize(cat_name)}.tex"
        try:
            out_path.write_text(text, encoding="utf-8")
            tqdm.write(f"[ok] {out_path}")
        except Exception as e:
            tqdm.write(f"[error] write failed for '{cat_name}': {e}")

        pbar.update(1)

    pbar.close()


# -------------------- hard-coded main --------------------
def main():
    JSON_PATH = Path("output/category.json")                  # your categories JSON (like in the message)
    PROMPT_PATH = Path("prompts/prompt_background.md")   # the improved background prompt
    PAPERS_DIR = Path("output")                          # directory with paper files; JSONs here get embedded
    OUTPUT_DIR = Path("output")                          # .tex per category
    MODEL_NAME = "models/gemini-2.5-pro"               # adjust if needed
    MAX_CATEGORIES = None                                # e.g., 2 to test

    run_generation(
        json_path=JSON_PATH,
        prompt_path=PROMPT_PATH,
        papers_dir=PAPERS_DIR,
        output_dir=OUTPUT_DIR,
        model_name=MODEL_NAME,
        max_categories=MAX_CATEGORIES,
    )


if __name__ == "__main__":
    main()
