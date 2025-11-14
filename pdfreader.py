
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# -------------------------
# 1. CONFIGURE GEMINI
# -------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found in .env file. Please create a .env file with GEMINI_API_KEY=<your_key>.")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("models/gemini-2.5-flash")

# -------------------------
# 2. READ PROMPT FROM MD FILE
# -------------------------
PROMPT_PATH = "prompt.md"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    base_prompt = f.read()

import os

# -------------------------
# 3. PDF INPUTS
# -------------------------
input_dir = "input"
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# List all PDF files in input folder
pdf_paths = [os.path.join(input_dir, fname) for fname in os.listdir(input_dir) if fname.lower().endswith('.pdf')]

# Upload PDFs
uploaded_files = [genai.upload_file(path) for path in pdf_paths]

# -------------------------
# 4. RUN EXTRACTION
# -------------------------
results = {}


# Process each PDF and save output as <pdfname>.json
for path, file in zip(pdf_paths, uploaded_files):
    original_pdfname = os.path.basename(path)
    json_filename = os.path.splitext(original_pdfname)[0] + ".json"
    output_path = os.path.join(output_dir, json_filename)
    print("Going to save as:", output_path)
    print(f"Processing: {file.name}")

    # Send MD prompt + PDF file as input sequence
    response = model.generate_content(
        [
            base_prompt,   # full MD prompt
            file           # PDF file content
        ]
    )

    # Gemini returns text — must be JSON because your prompt enforces it
    print("Saving now...")
    try:
        parsed_json = json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback: strip code fences if present
        print("⚠️ Model output was not valid JSON. Trying to strip code fences.")
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[len('```json'):].strip()
        if text.startswith('```'):
            text = text[len('```'):].strip()
        if text.endswith('```'):
            text = text[:-len('```')].strip()
        try:
            parsed_json = json.loads(text)
        except json.JSONDecodeError:
            print("⚠️ Still not valid JSON. Saving raw output.")
            parsed_json = {"raw_output": response.text}

    # Save output as <output_dir>/<original_pdfname>.json
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, indent=4, ensure_ascii=False)
    print(f"✅ Saved structured output to {output_path}")
