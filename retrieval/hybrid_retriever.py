"""Hybrid retrieval that fuses dense FAISS and BM25 with RRF."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from retrieval.vector_store import VectorStore


class HybridRetriever:
    """Production retriever that merges dense and lexical signals."""

    def __init__(self, processed_dir: str | Path) -> None:
        self.vector_store = VectorStore(processed_dir=processed_dir)
        self.documents = self.vector_store.metadata
        self.tokenized_corpus = [(doc.get("text", "") or "").lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def bm25_search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        query_tokens = query.lower().split()
        raw_scores = self.bm25.get_scores(query_tokens)
        max_score = float(np.max(raw_scores)) if len(raw_scores) > 0 else 0.0
        if max_score == 0.0:
            return []

        normalized = raw_scores / max_score
        top_indices = np.argsort(normalized)[::-1][:top_k]

        results: list[dict[str, Any]] = []
        for rank, idx in enumerate(top_indices, start=1):
            doc = self.documents[int(idx)]
            results.append(
                {
                    "rank": rank,
                    "bm25_score": float(normalized[idx]),
                    "chunk_id": doc.get("chunk_id"),
                    "text": doc.get("text", ""),
                    "book_title": doc.get("book_title", "Unknown"),
                    "page_number": doc.get("page_number", "Unknown"),
                    "author": doc.get("author", "Unknown"),
                    "source_pdf": doc.get("source_pdf"),
                }
            )
        return results

    def hybrid_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        dense_results = self.vector_store.dense_search(query, top_k=10)
        bm25_results = self.bm25_search(query, top_k=10)

        dense_rank_map = {item["chunk_id"]: item["rank"] for item in dense_results if item.get("chunk_id")}
        bm25_rank_map = {item["chunk_id"]: item["rank"] for item in bm25_results if item.get("chunk_id")}

        metadata_map: dict[str, dict[str, Any]] = {}
        for item in dense_results + bm25_results:
            chunk_id = item.get("chunk_id")
            if chunk_id and chunk_id not in metadata_map:
                metadata_map[chunk_id] = item

        all_chunk_ids = set(dense_rank_map.keys()) | set(bm25_rank_map.keys())
        k = 60

        fused_rows: list[dict[str, Any]] = []
        for chunk_id in all_chunk_ids:
            dense_rank = dense_rank_map.get(chunk_id, 1000)
            bm25_rank = bm25_rank_map.get(chunk_id, 1000)
            rrf_score = (1.0 / (k + dense_rank)) + (1.0 / (k + bm25_rank))
            meta = metadata_map[chunk_id]
            fused_rows.append(
                {
                    "chunk_id": chunk_id,
                    "text": meta.get("text", ""),
                    "book_title": meta.get("book_title", "Unknown"),
                    "page_number": meta.get("page_number", "Unknown"),
                    "author": meta.get("author", "Unknown"),
                    "source_pdf": meta.get("source_pdf"),
                    "dense_rank": dense_rank,
                    "bm25_rank": bm25_rank,
                    "rrf_score": float(rrf_score),
                }
            )

        fused_rows.sort(key=lambda x: x["rrf_score"], reverse=True)
        output: list[dict[str, Any]] = []
        for rank, row in enumerate(fused_rows[:top_k], start=1):
            row["rank"] = rank
            output.append(row)
        return output

    def loaded_books(self) -> list[str]:
        titles = sorted({(doc.get("book_title") or "Unknown") for doc in self.documents})
        return titles
