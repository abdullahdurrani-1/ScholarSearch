"""Dense retrieval over FAISS for ScholarSearch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from config.settings import EMBEDDING_MODEL


class VectorStore:
    """Loads FAISS and metadata, then serves dense semantic search."""

    def __init__(self, processed_dir: str | Path, embedding_model_name: str = EMBEDDING_MODEL) -> None:
        self.processed_dir = Path(processed_dir)
        self.embedding_model_name = embedding_model_name
        self.model = self._load_model()
        self.index = self._load_index()
        self.metadata = self._load_metadata()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(self.embedding_model_name)
        except Exception:
            # Allow API startup without heavy model runtime; hybrid retriever can still serve BM25 results.
            return None

    def _load_index(self):
        index_path = self.processed_dir / "faiss_index.bin"
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        return faiss.read_index(str(index_path))

    def _load_metadata(self) -> list[dict[str, Any]]:
        metadata_path = self.processed_dir / "chunk_metadata.json"
        fallback_path = self.processed_dir / "chunks.json"

        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        if fallback_path.exists():
            with open(fallback_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError("Neither chunk_metadata.json nor chunks.json was found in data/processed")

    def dense_search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        if self.model is None:
            return []

        query_vec = self.model.encode([query], convert_to_numpy=True).astype(np.float32)
        faiss.normalize_L2(query_vec)
        scores, indices = self.index.search(query_vec, top_k)

        results: list[dict[str, Any]] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
            if idx < 0 or idx >= len(self.metadata):
                continue
            hit = self.metadata[idx]
            results.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "chunk_id": hit.get("chunk_id"),
                    "text": hit.get("text", ""),
                    "book_title": hit.get("book_title", "Unknown"),
                    "page_number": hit.get("page_number", "Unknown"),
                    "author": hit.get("author", "Unknown"),
                    "source_pdf": hit.get("source_pdf"),
                }
            )
        return results

    @property
    def total_chunks(self) -> int:
        return len(self.metadata)
