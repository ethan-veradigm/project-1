"""
Candidate model: queries an Azure OpenAI deployment with a PubMedQA question
and parses its structured yes/no/maybe answer.
"""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from utils import (
    EvalConfig,
    PubMedQASample,
    CandidateResponse,
    CANDIDATE_SYSTEM_PROMPT,
)


def _build_user_message(sample: PubMedQASample) -> str:
    """Format the question + context into the user turn."""
    return (
        f"QUESTION:\n{sample.question}\n\n"
        f"CONTEXT:\n{sample.context}\n\n"
        "Answer the question using only the context above."
    )


def _parse_response(raw: str) -> tuple[str, str, str, str | None]:
    """
    Parse the model's JSON response.

    Returns (answer, reasoning, key_evidence, error).
    error is None on success.
    """
    # Strip markdown code fences if the model wraps its output
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return "", "", "", f"JSON parse error: {exc} | raw: {raw[:300]}"

    answer = str(data.get("answer", "")).strip().lower()
    reasoning = str(data.get("reasoning", "")).strip()
    key_evidence = str(data.get("key_evidence", "")).strip()

    if answer not in ("yes", "no", "maybe"):
        return answer, reasoning, key_evidence, (
            f"Unexpected answer value '{answer}'; expected yes/no/maybe."
        )

    return answer, reasoning, key_evidence, None


async def run_candidate(
    client: AsyncOpenAI,
    config: EvalConfig,
    sample: PubMedQASample,
) -> CandidateResponse:
    """
    Call the candidate deployment for one sample and return a CandidateResponse.

    Never raises — errors are captured in CandidateResponse.error.
    """
    user_msg = _build_user_message(sample)
    raw = ""

    try:
        response = await client.chat.completions.create(
            model=config.candidate_deployment,
            messages=[
                {"role": "system", "content": CANDIDATE_SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=config.candidate_temperature,
            timeout=config.request_timeout,
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        return CandidateResponse(
            answer="",
            reasoning="",
            key_evidence="",
            raw_content=raw,
            error=f"API error: {exc}",
        )

    answer, reasoning, key_evidence, error = _parse_response(raw)
    return CandidateResponse(
        answer=answer,
        reasoning=reasoning,
        key_evidence=key_evidence,
        raw_content=raw,
        error=error,
    )
