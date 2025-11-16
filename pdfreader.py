import os
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from tqdm import tqdm
import google.generativeai as genai

LEADING_NUM_RE = re.compile(r"^\s*(\d+)\s*\.")


def extract_id(name: str) -> int | None:
    m = LEADING_NUM_RE.match(name)
    return int(m.group(1)) if m else None


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json") :].strip()
    if text.startswith("```"):
        text = text[len("```") :].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def parse_json(raw: str, pdf_name: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = strip_code_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            tqdm.write(f"⚠️  invalid JSON for {pdf_name}, saving raw output")
            return {"raw_output": raw}


def process_pdf(
    pdf_path: str,
    prompt: str,
    output_dir: Path,
    model_name: str,
) -> Path:
    file_handle = genai.upload_file(pdf_path)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt, file_handle])

    pdf_name = Path(pdf_path).name
    data = parse_json(response.text, pdf_name)
    data["id"] = extract_id(pdf_name)

    out_path = output_dir / f"{Path(pdf_name).stem}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return out_path


def run(
    input_dir: str,
    output_dir: str,
    prompt_path: str,
    model_name: str,
    max_workers: int,
) -> None:
    load_dotenv()
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

    prompt = Path(prompt_path).read_text(encoding="utf-8")
    pdf_paths = [str(p) for p in Path(input_dir).glob("*.pdf")]

    if not pdf_paths:
        tqdm.write(f"No PDFs found in {input_dir}")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(process_pdf, p, prompt, Path(output_dir), model_name)
            for p in pdf_paths
        ]
        bar = tqdm(total=len(futures), desc="Processing PDFs", unit="pdf")
        for f in as_completed(futures):
            f.result()
            bar.update()
        bar.close()


def main() -> None:
    run(
        input_dir="input",
        output_dir="output",
        prompt_path="prompts/prompt-pdf-reader-background.md",
        model_name="models/gemini-2.5-pro",
        max_workers=4,
    )


if __name__ == "__main__":
    main()
