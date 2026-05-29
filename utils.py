"""
Shared config, data models, and constants for the PubMedQA eval harness.
All other modules import from here:  from utils import EvalConfig, EvalResult, ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class EvalConfig:
    """All runtime settings for the eval harness."""

    # Azure OpenAI connection
    azure_endpoint: str
    azure_api_key: str
    # Deployment names (user-supplied — no defaults)
    candidate_deployment: str = ""
    judge_deployment: str = ""

    # Dataset
    dataset_name: str = "qiaojin/PubMedQA"
    dataset_split: str = "pqa_labeled"        # pqa_labeled | pqa_artificial
    dataset_partition: str = "train"           # pqa_labeled only has 'train'
    dataset_subset: Optional[str] = None       # row-level subset filter, e.g. "reasoning_required"
    max_samples: Optional[int] = 1             # None = run all

    # Model temperatures
    candidate_temperature: float = 0.0
    judge_temperature: float = 0.0

    # Concurrency / reliability
    max_concurrent: int = 5
    request_timeout: int = 60            # seconds per API call

    # Output
    output_path: Path = Path("results/results.json")

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "EvalConfig":
        """Load config from a .env file and environment variables."""
        load_dotenv(env_file, override=False)

        missing = []
        for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY",
                    "CANDIDATE_DEPLOYMENT", "JUDGE_DEPLOYMENT"):
            if not os.getenv(key):
                missing.append(key)
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Copy .env.example to .env and fill them in."
            )

        return cls(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/").removesuffix("/responses"),
            azure_api_key=os.environ["AZURE_OPENAI_API_KEY"],
            candidate_deployment=os.environ["CANDIDATE_DEPLOYMENT"],
            judge_deployment=os.environ["JUDGE_DEPLOYMENT"],
            dataset_split=os.getenv("DATASET_SPLIT", "pqa_labeled"),
            dataset_partition=os.getenv("DATASET_PARTITION", "train"),
            dataset_subset=os.getenv("DATASET_SUBSET") or None,
            candidate_temperature=float(os.getenv("CANDIDATE_TEMPERATURE", "0.0")),
            judge_temperature=float(os.getenv("JUDGE_TEMPERATURE", "0.0")),
            max_samples=int(os.environ["MAX_SAMPLES"]) if os.getenv("MAX_SAMPLES") else None,
            max_concurrent=int(os.getenv("MAX_CONCURRENT", "5")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "60")),
            output_path=Path(os.getenv("OUTPUT_PATH", "eval_results.json")),
        )

    def override_from_args(self, args) -> None:
        """Apply CLI argument overrides on top of env-loaded values."""
        if getattr(args, "candidate_deployment", None):
            self.candidate_deployment = args.candidate_deployment
        if getattr(args, "judge_deployment", None):
            self.judge_deployment = args.judge_deployment
        if getattr(args, "dataset_split", None):
            self.dataset_split = args.dataset_split
        if getattr(args, "dataset_partition", None):
            self.dataset_partition = args.dataset_partition
        if getattr(args, "dataset_subset", None):
            self.dataset_subset = args.dataset_subset
        if getattr(args, "max_samples", None) is not None:
            self.max_samples = args.max_samples
        if getattr(args, "max_concurrent", None) is not None:
            self.max_concurrent = args.max_concurrent
        if getattr(args, "output", None):
            self.output_path = Path(args.output)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PubMedQASample:
    """One PubMedQA question with its context and gold answer."""
    pubid: str
    question: str
    context: str               # Context paragraphs joined into a readable block
    context_labels: list       # Section labels e.g. ["METHODS", "RESULTS"]
    long_answer: str           # Gold long-form answer
    gold_label: str            # Gold label: yes | no | maybe


@dataclass
class CandidateResponse:
    """Structured answer produced by the candidate model."""
    answer: str          # yes | no | maybe
    reasoning: str       # Model's chain-of-thought explanation
    key_evidence: str    # Most important evidence from the context
    raw_content: str     # Raw text the API returned (for debugging)
    error: Optional[str] = None   # Populated if the call or JSON parse failed


@dataclass
class JudgeResponse:
    """Structured evaluation produced by the judge model."""
    candidate_label: str     # Label the judge extracted from the candidate answer
    label_match: bool        # candidate_label == gold_label
    verdict: str             # correct | incorrect | partially_correct
    reasoning: str           # Step-by-step judge analysis
    quality_score: int       # 1–5 reasoning quality score
    raw_content: str         # Raw text the API returned (for debugging)
    error: Optional[str] = None


@dataclass
class EvalResult:
    """Complete evaluation record for one PubMedQA sample."""
    sample: PubMedQASample
    candidate_response: Optional[CandidateResponse]
    judge_response: Optional[JudgeResponse]
    status: str   # success | candidate_error | judge_error

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON output."""
        out: dict = {
            "pubid": self.sample.pubid,
            "question": self.sample.question,
            "context": self.sample.context,
            "context_labels": self.sample.context_labels,
            "long_answer": self.sample.long_answer,
            "gold_label": self.sample.gold_label,
            "status": self.status,
            "candidate": None,
            "judge": None,
        }

        if self.candidate_response:
            out["candidate"] = {
                "answer": self.candidate_response.answer,
                "reasoning": self.candidate_response.reasoning,
                "key_evidence": self.candidate_response.key_evidence,
                "raw_content": self.candidate_response.raw_content,
                "error": self.candidate_response.error,
            }

        if self.judge_response:
            out["judge"] = {
                "candidate_label": self.judge_response.candidate_label,
                "label_match": self.judge_response.label_match,
                "verdict": self.judge_response.verdict,
                "reasoning": self.judge_response.reasoning,
                "quality_score": self.judge_response.quality_score,
                "raw_content": self.judge_response.raw_content,
                "error": self.judge_response.error,
            }

        return out


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

CANDIDATE_SYSTEM_PROMPT = """\
You are an expert biomedical researcher answering questions based on PubMed research abstracts.

You will receive a biomedical question and relevant context excerpts from PubMed abstracts.

Instructions:
1. Carefully read the question and all provided context sections.
2. Decide whether the answer is "yes", "no", or "maybe":
   - "yes"   – the evidence clearly supports a positive answer.
   - "no"    – the evidence clearly contradicts or refutes the premise.
   - "maybe" – the evidence is mixed, insufficient, or inconclusive.
3. Write detailed reasoning grounded in the context.
4. Quote or paraphrase the key evidence that most strongly supports your answer.

Return ONLY valid JSON — no markdown fences, no extra keys:
{
  "answer": "<yes|no|maybe>",
  "reasoning": "<your detailed explanation>",
  "key_evidence": "<the most important supporting evidence from the context>"
}"""

JUDGE_SYSTEM_PROMPT = """\
You are an expert biomedical AI evaluator assessing the quality and correctness of AI-generated \
answers to PubMedQA questions.

You will receive:
  1. The biomedical research question.
  2. The relevant context excerpts.
  3. The ground-truth answer label (yes / no / maybe).
  4. The candidate AI model's JSON response.

Your task:
  Step 1 – Identify the label the candidate gave (yes / no / maybe).
  Step 2 – Check whether it matches the ground-truth label.
  Step 3 – Read the context carefully and reason about whether the candidate's explanation \
is scientifically sound and well-supported.
  Step 4 – Assign a verdict:
             "correct"   – the candidate's label matches the ground-truth label.
             "incorrect" – the candidate's label does NOT match the ground-truth label.
  Step 5 – Write a thorough explanation covering:
             • whether the label is right and why,
             • what the candidate got right or wrong in their reasoning,
             • what a better answer would look like if the response was lacking.
  Step 6 – Score the candidate's reasoning quality from 1 to 5:
             1 = completely wrong or irrelevant
             2 = mostly incorrect, some valid points
             3 = partially correct, mixed quality
             4 = mostly correct with minor issues
             5 = excellent, well-reasoned, evidence-based

Return ONLY valid JSON — no markdown fences, no extra keys:
{
  "candidate_label": "<yes|no|maybe>",
  "label_match": <true|false>,
  "verdict": "<correct|incorrect>",
  "reasoning": "<your detailed step-by-step evaluation>",
  "quality_score": <1|2|3|4|5>
}"""
