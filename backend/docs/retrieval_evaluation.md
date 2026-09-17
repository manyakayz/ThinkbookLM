# Milestone 2 — Manual Retrieval Evaluation

This document establishes a **baseline** for semantic retrieval quality using
Qwen3-Embedding-0.6B + ChromaDB.  It is NOT a claim of measured F1/NDCG scores;
it is a structured record of sample queries so future milestones can compare
against this baseline after RAG improvements.

---

## Setup

Before running queries, ensure:

```
ollama serve
ollama pull qwen3-embedding:0.6b
# backend running:  uvicorn app.main:app --reload
# frontend running: npm run dev
```

Upload at least one test document into a notebook and confirm
`indexing_status = indexed` on the document card.

---

## Test Documents Used

| # | Filename | Type | Pages / Size | Content summary |
|---|---|---|---|---|
| 1 | *(fill in your test document)* | PDF/DOCX/TXT | — | — |

> **Instructions**: Upload 1–3 real documents you have access to. For each,
> write 1–2 sentences describing what it contains, then fill in the query
> table below.

---

## Query Evaluation Table

For each query, record the expected result and the actual top-3 retrieved chunks.

### Query 1 — Exact Wording

| Field | Value |
|---|---|
| Query text | *(copy a sentence from your document verbatim)* |
| Expected document | — |
| Expected page / chunk | — |
| Top-1 retrieved doc | — |
| Top-1 chunk index | — |
| Top-1 distance | — |
| Top-1 correct? | ✅ / ❌ |
| Top-3 correct? | ✅ / ❌ |
| Notes | |

---

### Query 2 — Paraphrased Wording

| Field | Value |
|---|---|
| Query text | *(paraphrase a key sentence from your document)* |
| Expected document | — |
| Expected page / chunk | — |
| Top-1 retrieved doc | — |
| Top-1 distance | — |
| Top-1 correct? | ✅ / ❌ |
| Top-3 correct? | ✅ / ❌ |
| Notes | |

---

### Query 3 — Conceptual Question

| Field | Value |
|---|---|
| Query text | *(ask a high-level question whose answer requires understanding)* |
| Expected document | — |
| Expected page / chunk | — |
| Top-1 retrieved doc | — |
| Top-1 distance | — |
| Top-1 correct? | ✅ / ❌ |
| Top-3 correct? | ✅ / ❌ |
| Notes | |

---

### Query 4 — Answer Exists in Only One Document (multi-doc test)

*Requires at least 2 documents uploaded.*

| Field | Value |
|---|---|
| Query text | *(topic unique to document 1, not mentioned in document 2)* |
| Expected document | Document 1 |
| Expected page / chunk | — |
| Top-1 retrieved doc | — |
| Did doc 2 appear in top-5? | Yes / No |
| Scope isolation correct? | ✅ / ❌ |
| Notes | |

---

### Query 5 — Similar Concept in Multiple Documents

*Requires at least 2 documents with overlapping topics.*

| Field | Value |
|---|---|
| Query text | *(topic that appears in multiple documents)* |
| Expected: both docs in top-5 | Yes / No |
| Top-5 doc coverage | — |
| Notes | |

---

### Query 6 — No Results Expected

| Field | Value |
|---|---|
| Query text | "xyzzy frobnicator quantum entanglement of purple elephants" |
| Expected | 0 results OR all distances > 1.5 |
| Actual result count | — |
| Lowest distance seen | — |
| Notes | |

---

## Observations

*(Fill in after running the queries.)*

### Embedding performance
- Model load time (first call): _____ s
- Avg embedding time per chunk (~1 200 chars): _____ ms
- Peak RAM delta observed: _____ MB

### Retrieval quality observations
- Exact-wording queries: generally hit top-1 / top-3?
- Paraphrased queries: how much does quality degrade?
- Conceptual queries: does the model "understand" the question?
- Known failures or surprising misses:

### Distance distribution
- Typical distance for a clearly correct chunk: ~_____
- Typical distance for a clearly wrong chunk:  ~_____
- Useful threshold for "probably relevant": < _____

---

## Known Limitations (Milestone 2)

- Retrieval is **semantic only** — no BM25 hybrid, no re-ranking.
- Chunks are character-based (1 200 chars, 200 overlap), not token-based.
  Chunk boundaries may split mid-sentence.
- `qwen3-embedding:0.6b` is a small model; larger models will likely
  produce better embeddings for complex conceptual queries.
- No caching: every query calls Ollama. Cold-start latency ~2–5 s on
  the target machine (i5-1135G7, 8 GB RAM).
- The Qwen3 **generation** model (Milestone 3) is NOT loaded here.

---

## What This Baseline Enables

Milestone 3 (RAG) will use these retrieved chunks as context for Ollama.
After RAG is implemented, re-run these queries and compare:

- Does the generated answer match the expected content?
- Does the cited passage correspond to the retrieved chunk?
- Does paraphrasing now matter less (because the LLM bridges the gap)?
