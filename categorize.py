#!/usr/bin/env python3
"""
merge_and_classify.py

Read all paper-summary JSON files, prepend a Markdown prompt, call Gemini
to classify the papers, and write the model’s JSON answer to
output/category.json.
"""

import json
import logging
import os
import glob
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm
import google.generativeai as genai

# ----------------------------------------------------------------------
# 1. INITIAL SET-UP
# ----------------------------------------------------------------------
load_dotenv()  # reads .env in the current working directory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env. Create .env with GEMINI_API_KEY=<your_key>."
    )

genai.configure(api_key=api_key)
model = genai.GenerativeModel("models/gemini-2.5-pro")
log.info("Gemini model initialised.")

# ----------------------------------------------------------------------
# 2. PATHS
# ----------------------------------------------------------------------
INPUT_DIR = Path("output")       # folder of *.json paper summaries
PROMPT_PATH = Path("prompts/prompt-categorizer.md") # classification / background-section prompt
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "category.json"
OUTPUT_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------------------
# 3. READ PROMPT + JSON FILES
# ----------------------------------------------------------------------
log.info("Loading prompt from %s", PROMPT_PATH)
with PROMPT_PATH.open("r", encoding="utf-8") as f:
    base_prompt = f.read()

paper_objects = []
json_paths = sorted(glob.glob(str(INPUT_DIR / "*.json")))
if not json_paths:
    raise RuntimeError(f"No .json files found in {INPUT_DIR}/")

log.info("Reading %d JSON files from %s", len(json_paths), INPUT_DIR)
for p in tqdm(json_paths, desc="Reading JSON"):
    with open(p, "r", encoding="utf-8") as jf:
        paper_objects.append(json.load(jf))

# ----------------------------------------------------------------------
# 4. BUILD THE MODEL INPUT
# ----------------------------------------------------------------------
full_prompt = (
    f"{base_prompt}\n\n"
    "# === Paper JSON objects ===\n"
    f"{json.dumps(paper_objects, indent=2)}"
)

# ----------------------------------------------------------------------
# 5. CALL GEMINI
# ----------------------------------------------------------------------
log.info("Sending request to Gemini (may take a while)…")
response = model.generate_content(full_prompt)

# ----------------------------------------------------------------------
# 6. WRITE RESULT
# ----------------------------------------------------------------------

text = response.text.strip()
if text.startswith("```json"):
    text = text[len("```json"):].strip()
if text.startswith("```"):
    text = text[len("```"):].strip()
if text.endswith("```"):
    text = text[:-len("```")].strip()
try:
    parsed = json.loads(text)
except json.JSONDecodeError:
    log.error("Still invalid JSON for %s. Saving raw output.")
    parsed = {"raw_output": response.text}
    

# Save result
with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
    json.dump(parsed, f_out, indent=4, ensure_ascii=False)

log.info("✅ Saved structured output to %s", OUTPUT_FILE)

