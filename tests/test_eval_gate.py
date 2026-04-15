from __future__ import annotations

from evaluation.run_eval import evaluate_retrieval


def test_retrieval_report_has_required_fields() -> None:
    report = evaluate_retrieval()
    assert "queries" in report
    assert "recall_at_5" in report
    assert "mrr" in report
    assert report["queries"] > 0
    assert 0.0 <= report["recall_at_5"] <= 1.0
    assert 0.0 <= report["mrr"] <= 1.0
