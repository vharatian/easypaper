# 🧠 Scientific Paper Information Extraction Prompt

**Role:**  
You are a *research scientist* conducting a **literature review** on *code review comment classification*.  
Your task is to carefully read and extract structured information from the provided scientific paper.

---

## 🎯 Extraction Instructions

Extract the following information **factually and concisely**, without interpretation or motivation.  
The final output **must be a single valid JSON object** with the following fields:

---

### **1. Paper Identification**
- **Title:** Extract the full title of the paper exactly as written.  
- **Citation Format:** Extract the first author’s last name followed by *et al.* (e.g., *Smith et al.*).  
- **Year of Publication:** Extract the publication year, if explicitly stated.

---

### **2. Summary (≤10 sentences)**
Provide a factual summary of what the authors **did** — not *why* they did it.  
Focus on:
- The problem they addressed (briefly, 1 sentence max)  
- The approach or method they proposed or evaluated  
- The experimental setup or evaluation framework  
- The key findings or results (avoid interpretation)  
- Talk about the important numbers they have reported (No need to have all the numbers but the important ones)

---

### **3. Dataset Description (≤10 sentences)**
Focus on how the data was obtained and prepared. Include:
- Whether they **collected** their own dataset or **reused** an existing one  
- If reused: include dataset name, original authors, paper title, and publication year  
- Whether the dataset was **refined, extended, or used as-is**  
- For collected datasets: specify  
  - **Data source** (e.g., GitHub, Gerrit, internal company data)  
  - **Number of repositories or projects**  
  - **Number of comments or datapoints**  
  - **Annotation process** (who annotated, how many annotators, annotation scheme)  
- Whether the dataset is **publicly available** or **private/internal**
- The size of the dataset, both in terms of sources like repositories and in terms of datapoints. 
- If the dataset is reused, don't extensively talk about how the dataset was collected a brief description of what it contains is enough. Make sure you mention if it was refined or extended, or modified in any way. 

---

### **4. Taxonomy of Comment Classification (≤10 sentences)**
Extract detailed information about the taxonomy used:
- Whether the taxonomy was **reused** or **newly proposed**  
- If reused: include taxonomy name, authors, paper title, and publication year  
- Any **refinements or modifications** made  
- **Number of levels or dimensions** in the taxonomy  
- **Number and names of high-level categories**  
- Any notes on **labeling guidelines or category examples**

---

### **5. Classification Method (≤5 sentences)**
Describe the technical approach for classification:
- Whether they used **Classical NLP**, **Machine Learning**, or **Large Language Models (LLMs)**  
- The **specific algorithms or models** used (e.g., SVM, Random Forest, BERT, GPT-4, etc.)  
- Whether they performed **fine-tuning**, **prompt-based classification**, or **zero/few-shot learning**  
- Key **features, embeddings, or architectures** used  
- Any **comparison baselines** or **evaluation metrics** reported  

---

## ⚙️ Output Format

Return the answer strictly as a valid JSON object that could be pared with standard tools (not Markdown, not a list, not explanations), containing the following keys only:

- `"title"`  
- `"authors"`  
- `"year_of_publication"`  
- `"summary_text"`  
- `"dataset_text"`  
- `"taxonomy_text"`  
- `"method_text"`  

---

## ✅ Additional Guidelines

- Strictly focus only on **what is explicitly mentioned** in the paper; do not infer or speculate.  
- Ignore any text related to **motivation**, **background theory**, or **literature review**.  
- If a section (e.g., taxonomy) is **not mentioned**, YOU MUST write “Not reported in the paper.”  
- Don't add any citation as they are breaking the flow of the JSON output. 
