"""Automated evaluation gate for CI/CD.

Fails the pipeline when retrieval quality drops below configured thresholds.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from evaluation.run_eval import evaluate_generation, evaluate_retrieval

MIN_RECALL_AT_5 = float(os.getenv("MIN_RECALL_AT_5", "0.70"))
MIN_MRR = float(os.getenv("MIN_MRR", "0.40"))
MIN_GROUNDEDNESS = float(os.getenv("MIN_GROUNDEDNESS", "0.70"))
REQUIRE_GENERATION_GATE = os.getenv("REQUIRE_GENERATION_GATE", "0") == "1"



def main() -> int:
    retrieval = evaluate_retrieval()
    generation = None
    run_generation = bool(os.getenv("GOOGLE_API_KEY"))

    if run_generation:
        generation = evaluate_generation()

    checks = {
        "retrieval_recall_at_5": retrieval["recall_at_5"] >= MIN_RECALL_AT_5,
        "retrieval_mrr": retrieval["mrr"] >= MIN_MRR,
    }

    if generation is not None:
        checks["generation_groundedness_rate"] = generation["groundedness_rate"] >= MIN_GROUNDEDNESS
        checks["generation_out_of_scope_guardrail"] = generation["out_of_scope_guardrail_pass_rate"] >= 1.0
    elif REQUIRE_GENERATION_GATE:
        checks["generation_gate_required_but_skipped"] = False

    passed = all(checks.values())

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "min_recall_at_5": MIN_RECALL_AT_5,
            "min_mrr": MIN_MRR,
            "min_groundedness": MIN_GROUNDEDNESS,
            "require_generation_gate": REQUIRE_GENERATION_GATE,
        },
        "checks": checks,
        "retrieval": retrieval,
        "generation": generation,
        "passed": passed,
    }

    output_dir = Path("evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "gate_report.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    if not passed:
        print("\nEvaluation gate failed.")
        return 1

    print("\nEvaluation gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
