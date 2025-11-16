import json
import re
from pathlib import Path


def collect_citations(input_dir: Path, output_file: Path) -> None:
    """Read *.json files whose name starts with a digit and build one .bib file."""
    bib_entries = []

    for json_path in sorted(input_dir.glob("*.json")):
        # Skip files whose basename does not start with a digit
        if not re.match(r"^\d", json_path.name):
            continue

        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            citation = data.get("citation-text")
            if citation:
                bib_entries.append(citation.strip())
        except (json.JSONDecodeError, OSError) as exc:
            # Ignore unreadable / malformed files but keep processing others
            print(f"⚠️  Skipped {json_path.name}: {exc}")

    if not bib_entries:
        print("No valid citation_text fields found – nothing written.")
        return

    output_file.write_text("\n\n".join(bib_entries), encoding="utf-8")
    print(f"✅  Wrote {len(bib_entries)} entries to {output_file}")


def main() -> None:
    # ------------------------------------------------------------------
    # Hard-coded parameters (edit here if you want different locations)
    # ------------------------------------------------------------------
    INPUT_DIR = Path("output")      # folder containing the *.json files
    OUTPUT_BIB = INPUT_DIR / "citations.bib"
    # ------------------------------------------------------------------

    collect_citations(INPUT_DIR, OUTPUT_BIB)


if __name__ == "__main__":
    main()
