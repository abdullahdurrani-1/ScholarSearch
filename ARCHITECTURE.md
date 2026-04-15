# ScholarSearch Architecture

## End-to-End Data Flow
1. PDFs are read from `data_pipeline/books/` and parsed page-by-page.
2. Cleaning removes page-number noise, line-break artifacts, and OCR garbage.
3. Clean text is chunked with overlap and metadata-rich `chunk_id`s.
4. Dense embeddings are built and indexed in FAISS.
5. BM25 lexical index is built over the same chunk corpus.
6. Hybrid retrieval merges dense + lexical candidates with RRF.
7. Generation consumes top-k chunks and answers with grounded citations.
8. FastAPI exposes `/query`, `/health`, `/feedback`, and `/stats`.
9. Streamlit and HTML dashboards call the API for interactive usage.

## Why These Components
- FAISS: low-latency dense retrieval on CPU-friendly workloads.
- BM25: exact-term recall for names, acronyms, and sparse tokens.
- RRF fusion: robust ranking when dense and BM25 scores use different scales.
- FastAPI: production-grade async service and clean OpenAPI integration.
- Streamlit + HTML dashboard: rapid demo plus deployable static-compatible UI.

## Bottlenecks and Mitigations
- Embedding throughput: batch processing and persisted `.npy` outputs.
- Retrieval cold start: load FAISS once during API startup.
- API quota limits: graceful fallback responses and retrieval-first previews.
- Debugability: citation metadata and request logs in `data/metadata/`.

## What Changes at 10x Scale
- Switch `IndexFlatIP` to IVF/HNSW or managed vector DB.
- Add distributed caching for frequent query embeddings.
- Move logs/feedback to a real datastore (Postgres/BigQuery).
- Add async worker queue for heavy evaluation jobs.
- Introduce A/B prompt experiments and canary rollout for model changes.
