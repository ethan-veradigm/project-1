"""
Judge model: queries a separate Azure OpenAI deployment to evaluate the
candidate's answer, producing a verdict, label-match check, and reasoning.
"""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from utils import (
    EvalConfig,
    PubMedQASample,
    CandidateResponse,
    JudgeResponse,
    JUDGE_SYSTEM_PROMPT,
)


def _build_user_message(
    sample: PubMedQASample,
    candidate: CandidateResponse,
) -> str:
    """Format everything the judge needs into a single user turn."""
    candidate_block = json.dumps(
        {
            "answer": candidate.answer,
            "reasoning": candidate.reasoning,
            "key_evidence": candidate.key_evidence,
        },
        indent=2,
    )

    return (
        f"QUESTION:\n{sample.question}\n\n"
        f"CONTEXT:\n{sample.context}\n\n"
        f"GROUND-TRUTH LABEL: {sample.gold_label}\n\n"
        f"CANDIDATE RESPONSE:\n{candidate_block}\n\n"
        "Evaluate the candidate response following your instructions."
    )


def _parse_response(raw: str, gold_label: str) -> tuple[str, bool, str, str, int, str | None]:
    """
    Parse the judge's JSON response.

    Returns (candidate_label, label_match, verdict, reasoning, quality_score, error).
    error is None on success.
    """
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return "", False, "", "", 0, f"JSON parse error: {exc} | raw: {raw[:300]}"

    candidate_label = str(data.get("candidate_label", "")).strip().lower()
    label_match = bool(data.get("label_match", False))
    verdict = str(data.get("verdict", "")).strip().lower()
    reasoning = str(data.get("reasoning", "")).strip()
    quality_score = int(data.get("quality_score", 0))

    errors = []
    if candidate_label not in ("yes", "no", "maybe"):
        errors.append(f"Unexpected candidate_label '{candidate_label}'")
    if verdict not in ("correct", "incorrect"):
        errors.append(f"Unexpected verdict '{verdict}'")
    if not (1 <= quality_score <= 5):
        errors.append(f"quality_score {quality_score} out of range 1–5")

    # Reconcile label_match in case the model got the boolean wrong
    computed_match = candidate_label == gold_label
    if label_match != computed_match:
        label_match = computed_match   # trust the labels, not the boolean

    return (
        candidate_label,
        label_match,
        verdict,
        reasoning,
        quality_score,
        "; ".join(errors) if errors else None,
    )


async def run_judge(
    client: AsyncOpenAI,
    config: EvalConfig,
    sample: PubMedQASample,
    candidate: CandidateResponse,
) -> JudgeResponse:
    """
    Call the judge deployment for one sample and return a JudgeResponse.

    Never raises — errors are captured in JudgeResponse.error.
    """
    user_msg = _build_user_message(sample, candidate)
    raw = ""

    try:
        response = await client.chat.completions.create(
            model=config.judge_deployment,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=config.judge_temperature,
            timeout=config.request_timeout,
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        return JudgeResponse(
            candidate_label="",
            label_match=False,
            verdict="",
            reasoning="",
            quality_score=0,
            raw_content=raw,
            error=f"API error: {exc}",
        )

    candidate_label, label_match, verdict, reasoning, quality_score, error = _parse_response(
        raw, sample.gold_label
    )
    return JudgeResponse(
        candidate_label=candidate_label,
        label_match=label_match,
        verdict=verdict,
        reasoning=reasoning,
        quality_score=quality_score,
        raw_content=raw,
        error=error,
    )
