"""Smoke evaluation for retrieval and generation behavior."""

from __future__ import annotations

import json
from statistics import mean

from config.settings import PROCESSED_DIR
from generation.rag_chain import RagChain
from retrieval.hybrid_retriever import HybridRetriever


def evaluate_retrieval() -> dict:
    retriever = HybridRetriever(PROCESSED_DIR)
    queries = [
        "What is gradient descent?",
        "How does dropout reduce overfitting?",
        "What is the difference between L1 and L2 regularization?",
        "How do attention mechanisms work in transformers?",
    ]

    hit_flags = []
    reciprocal_ranks = []
    for query in queries:
        results = retriever.hybrid_search(query, top_k=5)
        hit = len(results) > 0
        rank = 1 if hit else 999
        hit_flags.append(1 if hit else 0)
        reciprocal_ranks.append(1.0 / rank)

    report = {
        "queries": len(queries),
        "recall_at_5": sum(hit_flags) / len(queries),
        "mrr": mean(reciprocal_ranks),
    }
    return report


def evaluate_generation() -> dict:
    retriever = HybridRetriever(PROCESSED_DIR)
    chain = RagChain(retriever)
    demo_questions = [
        "What is gradient descent?",
        "How does Adam differ from SGD?",
        "What is quantum computing?",
    ]

    outputs = [chain.generate_answer(q) for q in demo_questions]
    grounded = [1 for o in outputs if len(o.get("citations", [])) > 0]
    out_of_scope_ok = 0
    for output in outputs:
        q = output.get("query", "").lower()
        a = output.get("answer", "").lower()
        if "quantum" in q and ("outside" in a or "cover" in a):
            out_of_scope_ok += 1

    return {
        "questions": len(demo_questions),
        "groundedness_rate": sum(grounded) / len(outputs),
        "out_of_scope_guardrail_pass_rate": out_of_scope_ok / 1,
        "sample_answers": outputs,
    }


if __name__ == "__main__":
    retrieval_report = evaluate_retrieval()
    generation_report = evaluate_generation()

    print("RETRIEVAL REPORT")
    print(json.dumps(retrieval_report, indent=2))
    print("\nGENERATION REPORT")
    print(json.dumps(generation_report, indent=2))
