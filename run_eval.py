"""
CLI entrypoint for the PubMedQA eval harness.

Usage examples:

  # Minimal — reads everything from .env
  python run_eval.py

  # Run 3 trials, saving eval_results_1.json, eval_results_2.json, eval_results_3.json
  python run_eval.py --trials 3

  # Override specific settings at runtime
  python run_eval.py \\
      --candidate-deployment gpt-4o \\
      --judge-deployment     gpt-4o-mini \\
      --dataset-split        pqa_labeled \\
      --max-samples          50 \\
      --output               results/run.json

  # Use a custom .env file
  python run_eval.py --env-file my_secrets.env
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from utils import EvalConfig
from dataset import load_pubmedqa
from evaluator import run_evaluation
from report import write_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PubMedQA evaluation harness (Azure OpenAI + LLM-as-judge)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Azure / deployment overrides
    parser.add_argument(
        "--candidate-deployment",
        metavar="NAME",
        help="Azure OpenAI deployment name for the candidate model "
             "(overrides CANDIDATE_DEPLOYMENT env var)",
    )
    parser.add_argument(
        "--judge-deployment",
        metavar="NAME",
        help="Azure OpenAI deployment name for the judge model "
             "(overrides JUDGE_DEPLOYMENT env var)",
    )

    # Dataset
    parser.add_argument(
        "--dataset-split",
        choices=["pqa_labeled", "pqa_artificial"],
        help="Which PubMedQA split to use (overrides DATASET_SPLIT env var)",
    )
    parser.add_argument(
        "--dataset-partition",
        choices=["train", "test"],
        help="Dataset partition to evaluate on (overrides DATASET_PARTITION env var)",
    )
    parser.add_argument(
        "--dataset-subset",
        metavar="NAME",
        help="Filter to a specific row-level subset within the split "
             "(e.g. 'reasoning_required'). Overrides DATASET_SUBSET env var.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        metavar="N",
        help="Limit evaluation to the first N samples (useful for smoke tests)",
    )

    # Concurrency
    parser.add_argument(
        "--max-concurrent",
        type=int,
        metavar="N",
        help="Maximum number of simultaneous API requests (overrides MAX_CONCURRENT env var)",
    )

    # Trials
    parser.add_argument(
        "--trials",
        type=int,
        default=3,
        metavar="N",
        help="Number of independent evaluation runs to perform. Each trial saves a "
             "separate file named <stem>_1.json, <stem>_2.json, etc.",
    )

    # Output
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Base path for the JSON report(s) (overrides OUTPUT_PATH env var). "
             "With --trials the trial number is inserted before the extension.",
    )

    # Env file
    parser.add_argument(
        "--env-file",
        default=".env",
        metavar="PATH",
        help="Path to the .env file containing API credentials",
    )

    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    # --- Load config ---------------------------------------------------------
    try:
        config = EvalConfig.from_env(env_file=args.env_file)
    except EnvironmentError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    config.override_from_args(args)

    trials = args.trials

    print("Eval harness starting with:")
    print(f"  Candidate deployment : {config.candidate_deployment}")
    print(f"  Judge deployment     : {config.judge_deployment}")
    print(f"  Dataset split        : {config.dataset_split} / {config.dataset_partition}")
    print(f"  Max samples          : {config.max_samples or 'all'}")
    print(f"  Max concurrent       : {config.max_concurrent}")
    print(f"  Trials               : {trials}")
    print(f"  Base output path     : {config.output_path}")

    # --- Load dataset (once — reused across all trials) ----------------------
    try:
        samples = load_pubmedqa(config)
    except Exception as exc:
        print(f"[ERROR] Failed to load dataset: {exc}", file=sys.stderr)
        return 1

    if not samples:
        print("[ERROR] No samples loaded — check dataset split/partition.", file=sys.stderr)
        return 1

    # --- Run trials ----------------------------------------------------------
    base   = config.output_path
    stem   = base.stem    # e.g. "eval_results"
    suffix = base.suffix  # e.g. ".json"
    parent = base.parent  # e.g. Path(".")

    # Sanitise model names so they're safe to use in filenames
    def _safe(name: str) -> str:
        return name.replace("/", "-").replace("\\", "-").replace(" ", "_")

    candidate_tag = _safe(config.candidate_deployment)
    judge_tag     = _safe(config.judge_deployment)
    named_stem    = f"{stem}_{candidate_tag}_judge-{judge_tag}"

    for trial in range(1, trials + 1):
        if trials > 1:
            trial_path = parent / f"{named_stem}_{trial}{suffix}"
            print(f"\n{'=' * 60}")
            print(f"  TRIAL {trial} of {trials}")
            print(f"{'=' * 60}")
        else:
            trial_path = parent / f"{named_stem}{suffix}"

        config.output_path = trial_path
        results = await run_evaluation(config, samples)
        write_report(results, trial_path)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
