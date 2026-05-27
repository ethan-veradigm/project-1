"""
Async evaluation loop.

For each PubMedQA sample:
  1. Call the candidate model.
  2. If successful, call the judge model.
  3. Collect an EvalResult.

A semaphore caps the number of in-flight requests at config.max_concurrent.
"""

from __future__ import annotations

import asyncio
from typing import Sequence

from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

from utils import EvalConfig, PubMedQASample, EvalResult
from candidate import run_candidate
from judge import run_judge


async def _evaluate_one(
    semaphore: asyncio.Semaphore,
    client: AsyncOpenAI,
    config: EvalConfig,
    sample: PubMedQASample,
    index: int,
) -> EvalResult:
    """Run the candidate → judge pipeline for a single sample."""
    async with semaphore:
        # --- Candidate -------------------------------------------------------
        candidate_resp = await run_candidate(client, config, sample)

        if candidate_resp.error and not candidate_resp.answer:
            # Hard failure: no usable answer, skip the judge
            return EvalResult(
                sample=sample,
                candidate_response=candidate_resp,
                judge_response=None,
                status="candidate_error",
            )

        # --- Judge -----------------------------------------------------------
        judge_resp = await run_judge(client, config, sample, candidate_resp)

        status = "success"
        if judge_resp.error and not judge_resp.verdict:
            status = "judge_error"

        return EvalResult(
            sample=sample,
            candidate_response=candidate_resp,
            judge_response=judge_resp,
            status=status,
        )


async def run_evaluation(
    config: EvalConfig,
    samples: Sequence[PubMedQASample],
) -> list[EvalResult]:
    """
    Evaluate all samples concurrently (bounded by config.max_concurrent).

    Returns results in the same order as the input samples.
    """
    client = AsyncOpenAI(
        base_url=config.azure_endpoint,
        api_key=config.azure_api_key,
    )

    semaphore = asyncio.Semaphore(config.max_concurrent)

    tasks = [
        _evaluate_one(semaphore, client, config, sample, i)
        for i, sample in enumerate(samples)
    ]

    print(f"\nRunning evaluation on {len(tasks)} samples "
          f"(max_concurrent={config.max_concurrent}) ...")

    results: list[EvalResult] = await tqdm_asyncio.gather(
        *tasks,
        desc="Evaluating",
        unit="sample",
    )

    await client.close()
    return results
