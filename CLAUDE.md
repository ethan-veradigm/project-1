# Project Overview

This project is a **PubMedQA evaluation harness** built in Python. The role here is that of a software developer building and maintaining an eval pipeline that uses one LLM to generate answers (the candidate) and a separate LLM to judge the quality of those answers (the judge).

## What this project does

- Loads questions from the **PubMedQA** dataset (via HuggingFace `qiaojin/PubMedQA`)
- Sends each question + context to a **candidate model** via the Azure OpenAI API, which answers yes / no / maybe with reasoning
- Passes the candidate's response to a **judge model** (also via Azure OpenAI), which evaluates correctness and provides step-by-step reasoning
- Saves results to a JSON report with per-sample detail and aggregate metrics
- Supports multiple independent trial runs, each saved to a separate file

## File structure

| File | Purpose |
|---|---|
| `utils.py` | Config (`EvalConfig`), data models, and prompt templates — import from here |
| `dataset.py` | PubMedQA loader with subset filtering |
| `candidate.py` | Candidate model logic |
| `judge.py` | Judge model logic |
| `evaluator.py` | Async eval loop (concurrent, semaphore-bounded) |
| `report.py` | JSON report generation and summary stats |
| `run_eval.py` | CLI entrypoint |
| `view.py` | Interactive result browser |

## Key conventions

- All shared types and constants live in `utils.py` — other modules do `from utils import ...`
- Both models are queried via `AsyncOpenAI` with `base_url` pointing to an Azure AI Services endpoint (`*.services.ai.azure.com/openai/v1`)
- The judge verdict is strictly `correct` or `incorrect` — no partial credit
- Output filenames include both deployment names, e.g. `eval_results_gpt-5.4-mini_judge-gpt-5.5_1.json`
- Credentials live in `.env` (gitignored) — copy structure from comments in that file
- Result files (`eval_results*.json`) are gitignored

## Running

```bash
pip install -r requirements.txt
python run_eval.py --trials 3 --max-samples 50
python view.py
```
