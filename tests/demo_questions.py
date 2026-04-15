"""Demo sanity checks for ScholarSearch retrieval and generation."""

from __future__ import annotations

from config.settings import PROCESSED_DIR
from generation.rag_chain import RagChain
from retrieval.hybrid_retriever import HybridRetriever


def run_demo_checks() -> None:
    retriever = HybridRetriever(PROCESSED_DIR)
    chain = RagChain(retriever)

    questions = [
        "What is gradient descent?",
        "How does dropout reduce overfitting?",
        "What is the difference between L1 and L2 regularization?",
        "What is quantum computing?",
    ]

    print("DEMO QUESTION CHECK")
    print("===================")

    for q in questions:
        result = chain.generate_answer(q, top_k=5)
        print(f"\nQ: {q}")
        print(f"chunks_used: {result.get('chunks_used')}")
        print(f"confidence: {result.get('confidence')}")
        print(f"answer preview: {result.get('answer', '')[:300]}")
        print(f"citations: {len(result.get('citations', []))}")


if __name__ == "__main__":
    run_demo_checks()
