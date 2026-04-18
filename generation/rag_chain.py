"""RAG generation chain with grounding, citations, and guardrails."""

from __future__ import annotations

import os
import warnings
from typing import Any

# Suppress deprecation warning for google.generativeai (stable but deprecated)
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import google.generativeai as genai

from config.settings import LLM_MODEL, TOP_K
from retrieval.hybrid_retriever import HybridRetriever


SYSTEM_PROMPT = """
You are ScholarSearch, a warm and accurate ML tutor.
Answer only from provided context chunks.
Cite naturally with book title and page inside sentences.
If context does not support an answer, clearly say it is out of scope.
Do not invent page numbers, books, or author claims.
""".strip()


class RagChain:
    """High-level answer generator used by API and UI layers."""

    def __init__(self, retriever: HybridRetriever, llm_model: str = LLM_MODEL) -> None:
        self.retriever = retriever
        self.llm_model_name = llm_model
        self.model = self._configure_model()

    def _configure_model(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model_name = self.llm_model_name
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        return genai.GenerativeModel(model_name)

    def build_prompt(self, user_query: str, retrieved_chunks: list[dict[str, Any]]) -> str:
        prompt = "SYSTEM INSTRUCTIONS:\n"
        prompt += SYSTEM_PROMPT + "\n\n"
        prompt += "CONTEXT:\n"
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            prompt += (
                f"[{idx}] Book: {chunk.get('book_title', 'Unknown')} | "
                f"Page: {chunk.get('page_number', 'Unknown')} | "
                f"RRF: {chunk.get('rrf_score', 0.0):.4f}\n"
            )
            prompt += f"{chunk.get('text', '')}\n\n"
        prompt += f"USER QUESTION:\n{user_query}\n"
        prompt += "\nReturn a concise, grounded explanation with natural inline citations."
        return prompt

    def _is_out_of_scope(self, query: str, chunks: list[dict[str, Any]]) -> bool:
        if not chunks:
            return True
        q = query.lower()
        hard_oos = ["blockchain", "cook", "roman empire", "gps", "quantum"]
        if any(token in q for token in hard_oos):
            return True
        return float(chunks[0].get("rrf_score", 0.0)) < 0.012

    def _generate_headline(self, query: str, chunks: list[dict[str, Any]]) -> str:
        """Generate a professional headline for the answer."""
        # Extract key terms from query
        words = query.split()
        important_words = [w for w in words if len(w) > 4 and w.lower() not in 
                          ['what', 'when', 'where', 'which', 'about', 'could', 'would', 'should']]
        
        if important_words:
            headline = " ".join(important_words[:3]).title()
        else:
            headline = query.title()
        
        # Add context from top chunk if available
        if chunks:
            try:
                # Extract first meaningful phrase from context
                context_text = chunks[0].get('text', '')[:100]
                if context_text:
                    headline = f"{headline}: {context_text.split('.')[0].title()}"
            except:
                pass
        
        return headline[:100]  # Limit headline length

    def _fallback_answer(self, query: str) -> str:
        return (
            "Hmm, that one is outside what my loaded ML/DS books cover right now. "
            "Try a question about machine learning, deep learning, statistics, or model evaluation."
        )

    def generate_answer(self, user_query: str, top_k: int = TOP_K) -> dict[str, Any]:
        chunks = self.retriever.hybrid_search(user_query, top_k=top_k)
        citations = [
            {
                "book": c.get("book_title", "Unknown"),
                "page": c.get("page_number", "Unknown"),
                "relevance": "high" if i < 2 else "medium",
                "chunk_id": c.get("chunk_id"),
            }
            for i, c in enumerate(chunks)
        ]

        if self._is_out_of_scope(user_query, chunks):
            answer_text = self._fallback_answer(user_query)
            return {
                "query": user_query,
                "headline": "Topic Out of Scope",
                "answer": answer_text,
                "citations": citations,
                "confidence": "low",
                "follow_up_questions": [
                    "Do you want a quick recap of gradient descent?",
                    "Should we compare L1 and L2 regularization?",
                    "Want a simple explanation of overfitting vs underfitting?",
                ],
                "chunks_used": len(chunks),
                "retrieval_scores": [float(c.get("rrf_score", 0.0)) for c in chunks],
            }

        if self.model is None:
            preview = (chunks[0].get("text", "")[:400] if chunks else "")
            answer = (
                "LLM API key is not configured, so this is a retrieval-grounded preview only:\n\n"
                + preview
            )
        else:
            prompt = self.build_prompt(user_query, chunks)
            response = self.model.generate_content(prompt)
            answer = getattr(response, "text", "") or "No model text returned."

        headline = self._generate_headline(user_query, chunks)
        return {
            "query": user_query,
            "headline": headline,
            "answer": answer,
            "citations": citations,
            "confidence": "high" if chunks and float(chunks[0].get("rrf_score", 0.0)) >= 0.02 else "medium",
            "follow_up_questions": [
                "Want a deeper mathematical view of this concept?",
                "Should we connect this to a real model training example?",
                "Do you want to compare this with a related method?",
            ],
            "chunks_used": len(chunks),
            "retrieval_scores": [float(c.get("rrf_score", 0.0)) for c in chunks],
        }
