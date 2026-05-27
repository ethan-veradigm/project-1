"""
Report generator.

Aggregates EvalResult objects into summary statistics and writes a single
JSON file with both the per-sample detail and the overall summary.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from utils import EvalResult


def _compute_summary(results: list[EvalResult]) -> dict:
    """Compute aggregate metrics from a list of EvalResult objects."""
    total = len(results)
    status_counts = Counter(r.status for r in results)

    # Only look at successful results for accuracy metrics
    successful = [r for r in results if r.status == "success"]
    n_success = len(successful)

    label_matches = [
        r.judge_response.label_match
        for r in successful
        if r.judge_response and r.judge_response.error is None
    ]
    n_judged = len(label_matches)
    accuracy = sum(label_matches) / n_judged if n_judged else 0.0

    verdict_counts = Counter(
        r.judge_response.verdict
        for r in successful
        if r.judge_response and r.judge_response.verdict
    )

    quality_scores = [
        r.judge_response.quality_score
        for r in successful
        if r.judge_response and r.judge_response.quality_score > 0
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    # Candidate label distribution
    candidate_labels = Counter(
        r.candidate_response.answer
        for r in results
        if r.candidate_response and r.candidate_response.answer
    )

    # Gold label distribution
    gold_labels = Counter(r.sample.gold_label for r in results)

    return {
        "total_samples": total,
        "status_counts": dict(status_counts),
        "n_judged": n_judged,
        "accuracy": round(accuracy, 4),
        "accuracy_pct": round(accuracy * 100, 2),
        "verdict_counts": dict(verdict_counts),
        "avg_quality_score": round(avg_quality, 3),
        "candidate_label_distribution": dict(candidate_labels),
        "gold_label_distribution": dict(gold_labels),
    }


def write_report(results: list[EvalResult], output_path: Path) -> None:
    """
    Write a single JSON report containing:
      - "summary": aggregate metrics
      - "results": per-sample detail list

    Args:
        results: All EvalResult objects from the evaluation run.
        output_path: Path to write the JSON file to.
    """
    summary = _compute_summary(results)

    report = {
        "summary": summary,
        "results": [r.to_dict() for r in results],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    # Print a brief summary to the terminal
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"  Total samples      : {summary['total_samples']}")
    print(f"  Successfully judged: {summary['n_judged']}")
    print(f"  Accuracy (label)   : {summary['accuracy_pct']}%")
    print(f"  Avg quality score  : {summary['avg_quality_score']} / 5")
    print(f"  Verdicts           : {summary['verdict_counts']}")
    print(f"  Status counts      : {summary['status_counts']}")
    print(f"\n  Full report saved  : {output_path.resolve()}")
    print("=" * 60)
