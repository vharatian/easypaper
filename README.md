# EasyPaper PDF Scientific Paper Extractor

## Usage

- Place your input PDF files in the `input/` folder.
- Run the script `pdfreader.py`.
- Extracted JSON outputs will be saved in the `output/` folder, with the same name as the input PDF (e.g., `input/codedoctor.pdf` → `output/codedoctor.json`).

## Requirements

- Python 3.8+
- Install dependencies:
  - `pip install google-generativeai python-dotenv`
- Create a `.env` file in the project root with:
  - `GEMINI_API_KEY=<your_api_key>`

## Model Selection

- The Gemini model used is set in `pdfreader.py`:
  - Change the line: `model = genai.GenerativeModel("models/gemini-2.5-flash")` to use a different model if needed.

## Notes

- If `.env` or `GEMINI_API_KEY` is missing, the script will raise an error.
- Output JSON is parsed from Gemini's response and cleaned of markdown code fences automatically.
