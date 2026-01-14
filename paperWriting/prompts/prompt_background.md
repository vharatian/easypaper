# 🧠 Prompt: Background Section Generation for Code Review Comment Classification

**Role:**\
You are an *expert scientist* in **Software Engineering**, preparing the **Background** section for a research paper on *code review comment classification*.

------------------------------------------------------------------------

## 🎯 Objective

You are provided with a set of papers, each represented as a JSON object with the following fields:

-   `"id"`\
-   `"title"`\
-   `"authors"`\
-   `"year_of_publication"`\
-   `"citation_text"` \
-   `"summary_text"`\
-   `"dataset_text"`\
-   `"taxonomy_text"`\
-   `"method_text"`

Your task is to synthesize these papers into a **coherent and well-structured background subsection** (up to **500 words**) 
suitable for inclusion in a top-tier scientific conference paper.

------------------------------------------------------------------------

## 🧩 Instructions

1.  **Section Title:**
    -   Include the title as a `\subsection{}` header at the beginning
        of your text.
    - You will be provided with the **subsection title** to use.
2.  **Structure:**
    -   Begin with a **brief summary** (2--3 sentences) introducing the
        focus of the subsection.\
    -   Follow a **chronological or thematic narrative**, highlighting
        major milestones, datasets, taxonomies, and methodological
        trends.\
    -   Reference papers naturally using overleaf citation style (e.g.,
        "Smith et al.\~`\cite{smith2021}`{=tex} proposed ...").\
    -   Integrate **historical progression**: for example, early
        supervised approaches → dataset creation → feature engineering →
        deep learning → LLM-based techniques.\
    -   If helpful, you may split into **two logical storylines** (e.g.,
        *dataset evolution* and *modeling advances*)---but ensure **all
        provided papers are cited**.
3.  **Content Expectations:**
    -   Write in a **formal, concise, and factual** academic tone.\
    -   Avoid bullet points, lists, or personal opinions.\
    -   Avoid complicated wording; prefer clarity.\
    -   Emphasize **relationships and contrasts** among works (e.g.,
        improvements, limitations, paradigm shifts).\
    -   Ensure that **every paper** is mentioned meaningfully within the
        narrative.
4.  **Citation and Formatting:**
    -   Use LaTeX formatting compatible with Overleaf. Just use `~\cite{citation name}`, no extra tag like `[=tex]` is required \
    -   When writing the author names in citations, use "et al." for papers with more than two authors.\
    -   All citations should assume corresponding entries exist in the
        `.bib` file.\
    -   The output must be plain text in LaTeX-ready form (no JSON,
        Markdown, or code blocks).

------------------------------------------------------------------------

## 🔍 Chain-of-Thought Reasoning (Internal Only)

You must follow these reasoning steps **internally** before producing the final answer.  
**Do not include these steps, intermediate notes, or any reasoning traces in the final output.**  
Only output the final LaTeX-ready subsection text.

1. **Paper Understanding and Tagging**
    -   For each paper, carefully read its `"summary_text"`, `"dataset_text"`, `"taxonomy_text"`, and `"method_text"`.\\
    -   Assign each paper to one or more conceptual roles, such as:
        -   *early supervised methods*  
        -   *dataset creation / curation*  
        -   *feature engineering / traditional ML*  
        -   *deep learning approaches*  
        -   *LLM-based or prompt-based methods*  
        -   *taxonomy design / refinement*  
        -   *evaluation frameworks or metrics*  

2. **Thematic or Chronological Grouping**
    -   Decide whether a **chronological** or **thematic** organization (or a mix of both) best fits the given set of papers.\\
    -   Group papers into 2–4 coherent blocks that form a logical storyline (e.g., *datasets first, then modeling advances*, or *taxonomies first, then learning methods*).\\
    -   Within each block, determine an order that shows **progression**, **contrast**, or **refinement** among the works.

3. **Identify Key Transitions and Contrasts**
    -   For each block, identify:
        -   What problem or gap the earlier works addressed.  
        -   How later works extend, refine, or challenge previous approaches (e.g., richer labels, larger datasets, better performance, new model families).\\
    -   Plan 1–2 sentences per block that explicitly highlight these transitions or contrasts.

4. **Outline the Subsection**
    -   Draft a **mental or implicit outline**:
        -   Introductory 2–3 sentences stating the overall evolution of code review comment classification.  
        -   2–4 paragraphs following your chosen storyline (datasets / taxonomies / methods / LLMs).  
        -   A closing sentence (optional) that briefly summarizes the current state or trend.\\
    -   Decide where each paper will be mentioned so that **all papers are covered** without redundancy.

5. **Map Papers to Citations**
    -   For each paper, determine its citation key from `"citation-text"` and plan how to reference it in a natural sentence using LaTeX citation style (e.g., `... as shown by <citation-text>.`).

6. **Generate the Final Text**
    -   Using the outline and groupings above, write a single, smooth narrative:
        -   Start with `\\subsection{<title>}`.  
        -   Follow with the introductory summary.  
        -   Elaborate each block with clear transitions and appropriate citations.  
        -   Ensure the total length does not exceed **500 words**.\\
    -   Do **not** expose or mention any of the internal grouping, tagging, or step-by-step reasoning process in the final output.

------------------------------------------------------------------------

### ✅ Output Format Example

\subsection{Evolution of Code Review Comment Classification Approaches}

The task of classifying code review comments has evolved significantly
over the past decade. Early studies, such as Smith et
al.\~`\cite{smith2018}`{=tex}, introduced manually curated datasets...\
...\
Recent work by Zhao et al.\~`\cite{zhao2025}`{=tex} demonstrated the
potential of instruction-tuned large language models...
