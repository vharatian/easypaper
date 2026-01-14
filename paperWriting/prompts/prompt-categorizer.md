You are an expert scientific researcher preparing the **Background** section of a paper on code review comment classification.

We have already digested several related papers into JSON objects with the following fields:

- "id"
- "title"
- "authors"
- "year_of_publication"
- "citation_text"
- "summary_text"
- "dataset_text"
- "taxonomy_text"
- "method_text"

You will receive a list of these JSON objects as input.

---

## Overall Goal

Your goal is to **group the papers into a maximum of 4 conceptual categories** that will become the **subsections of the Background section**. You can have a lower number of categories if adding a new subcategory does not make sense. 

---

## Deliberate Reasoning (Chain-of-Thought)

Before you produce the final answer, **think through the task step by step**:

1. Carefully read all papers and note their main focus based on `summary_text`, `dataset_text`, `taxonomy_text`, and `method_text`.
2. Infer a set of high-level themes that best organize these papers into a coherent structure for a Background section.
3. Decide which papers belong to which themes, based on their primary contribution or emphasis.
4. Resolve borderline cases by choosing the **single most relevant** category, unless there is a very strong reason to assign a paper to more than one.

Do this reasoning **internally**.  
**Do not** include your intermediate reasoning, notes, or explanations in the final output.  
The **only** content you should output is the final JSON structure described below.

---

## Task Instructions

1. **Define categories**
   - Create high-level, *meaningful* categories.
   - Each category should correspond to a coherent theme that could be used as a subsection title in a Background/Related Work section.
   - Category names must be:
     - Concise (a few words)
     - Descriptive (reflecting the shared theme of the papers in that category)
     - Written in **Title Case** (e.g., `"LLM-Based Zero-Shot Classification"`).

2. **Assign papers to categories**
   - Assign **each paper to at least one category**.
   - Prefer assigning a paper to the **single most relevant** category.
   - Only assign a paper to multiple categories if this is clearly justified by its content (e.g., it equally covers two distinct themes).
   - When listing papers under each category, use:
     - `"id"` from the JSON
     - `"title"` from the JSON

---

## Output Format (Strict)

Your output **must** be:

- Valid **JSON**
- A **JSON array** of category objects
- **No explanations, no comments, no citations, no markdown** — only the JSON structure

Each category object must have this structure:

- `"category_name"`: the name of the category (string)
- `"papers"`: a list of paper objects, where each paper object has:
  - `"id"`: the paper id (string)
  - `"title"`: the paper title (string)

Conceptual example of the required shape:

```json
[
  {
    "category_name": "Example Category Name",
    "papers": [
      {
        "id": "paper-1-id",
        "title": "Paper 1 Title"
      },
      {
        "id": "paper-2-id",
        "title": "Paper 2 Title"
      }
    ]
  },
  {
    "category_name": "Another Category Name",
    "papers": [
      {
        "id": "paper-3-id",
        "title": "Paper 3 Title"
      }
    ]
  }
]
```

Return **only** this JSON. Do **not** include any additional text before or after the JSON.



