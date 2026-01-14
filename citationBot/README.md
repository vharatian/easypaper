## Citation Bot

This folder contains a small pipeline that, given **a target paper** and **a conference program committee**, finds PC papers that are most similar to your paper by abstract.

The pipeline has four main steps:

1. Scrape the PC roster from the conference website → `pc_members.csv`
2. Resolve PC members to OpenAlex author profiles → `authors.csv`
3. Download each author's papers from OpenAlex → CSVs under `files/alex_papers/`
4. Rank all papers by similarity to your paper's abstract → `citation_candidates.csv`

All paths and high‑level settings are centralized in `config.py`.

---

## 1. Setup

- **Python version**: 3.9+ is recommended.
- From the **project root**, install dependencies:

```bash
pip install -r requirements.txt
```

- Then change into the `citationBot` folder (all later commands assume this):

```bash
cd citationBot
```

- Ensure the `files/` directory exists (it will be created automatically by the scripts if missing).

---

## 2. Configure your paper & conference

From inside the `citationBot` folder, open `config.py` and set:

- **`PAPER_TITLE`**: title of the paper you want to find citations for.
- **`PAPER_ABSTRACT`**: full abstract text of your paper.
- **`NUM_RELEVANT_PAPERS`**: how many top similar papers to keep (e.g., `200`).
- **`CONFERENCE_WEBSITE`**: URL of the conference PC page you want to scrape.

You normally only need to edit this single file to switch to a new paper or a new conference.

---

## 3. Step‑by‑step pipeline

All commands below assume your shell is in the `citationBot` folder:

### 3.1 Collect PC members (`collect_authors.py`)

This script:
- Downloads the PC roster from `CONFERENCE_WEBSITE`.
- Parses names, roles, affiliations, and countries.
- Writes `pc_members.csv` under `files/`.

Run:

```bash
python collect_authors.py
```

Expected output:
- `files/pc_members.csv` with columns: `Name,Role,Affiliation,Country`.

### 3.2 Resolve authors in OpenAlex (`alex_find_profiles.py`)

This script:
- Reads `files/pc_members.csv`.
- Calls the OpenAlex **Institutions** and **Authors** APIs.
- Tries to match each PC member to an OpenAlex author ID.
- Writes `files/authors.csv`.

Run:

```bash
python alex_find_profiles.py
```

Expected output:
- `files/authors.csv` with columns like: `input_name,author_id,name,url,homepage,hindex,affiliations,confidence`.

> If you see warnings about missing matches, that's normal for some names; the script only keeps confident matches.

### 3.3 Download each author's papers (`alex_collect_papers.py`)

This script:
- Reads `files/authors.csv`.
- For each author, crawls their works from OpenAlex.
- Writes one CSV per author under `files/alex_papers/` containing:
  - `title,year,citation_count,conference_link,pdf_link,abstract`

Before running, you may optionally adjust in `alex_collect_papers.py`:
- `YEAR_MIN` to limit papers by publication year.
- `MAILTO` to your email (recommended by OpenAlex).

Run:

```bash
python alex_collect_papers.py
```

Expected outputs:
- Folder `files/alex_papers/` containing one CSV per author.

### 3.4 Find related papers (`find_related_papers.py`)

This script:
- Reads all CSVs in `files/alex_papers/`.
- Embeds all abstracts and your query abstract.
- Computes similarity (using Sentence‑Transformers if available, otherwise TF‑IDF).
- Sorts by similarity and keeps the top `NUM_RELEVANT_PAPERS`.
- Writes a final ranked CSV of candidate citations.

Run:

```bash
python find_related_papers.py
```

Expected output:
- `files/citation_candidates.csv` with columns:
  - `candidate_title,candidate_abstract,source_csv,similarity,rank`

These are the **PC members' papers most similar to your paper**, ready for manual inspection and use as citation candidates.

---

## 4. Typical full run

From the project root:

```bash
cd citationBot
python collect_authors.py
python alex_find_profiles.py
python alex_collect_papers.py
python find_related_papers.py
```

After these finish, open `files/citation_candidates.csv` in a spreadsheet or editor and inspect the top‑ranked papers.

