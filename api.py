"""
FastAPI backend for the PubMedQA eval dashboard.

Endpoints:
  GET  /api/config              – return .env defaults for the run form
  GET  /api/files               – list all eval_results*.json files
  GET  /api/results/{filename}  – return parsed results JSON
  POST /api/run                 – stream eval run output (SSE)

Run with:
  uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="PubMedQA Eval API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    candidate_deployment: str
    judge_deployment: str
    dataset_split: str = "pqa_labeled"
    dataset_partition: str = "train"
    max_samples: int = 10          # 0 = run all
    max_concurrent: int = 5
    trials: int = 3
    output: str = "results/results.json"
    candidate_temperature: float = 0.0
    judge_temperature: float = 0.0


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/config")
def get_config() -> dict:
    """Return .env values that pre-fill the run form."""
    env = dotenv_values(PROJECT_ROOT / ".env")
    return {
        "candidate_deployment": env.get("CANDIDATE_DEPLOYMENT", ""),
        "judge_deployment":     env.get("JUDGE_DEPLOYMENT", ""),
        "dataset_split":        env.get("DATASET_SPLIT", "pqa_labeled"),
        "dataset_partition":    env.get("DATASET_PARTITION", "train"),
        "max_samples":          int(env.get("MAX_SAMPLES", 10) or 10),
        "max_concurrent":       int(env.get("MAX_CONCURRENT", 5)),
        "candidate_temperature": float(env.get("CANDIDATE_TEMPERATURE", 0.0)),
        "judge_temperature":    float(env.get("JUDGE_TEMPERATURE", 0.0)),
    }


@app.get("/api/files")
def list_files() -> list[str]:
    """Return sorted list of eval result filenames in the project root."""
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    return sorted(p.name for p in results_dir.iterdir() if p.is_file() and not p.name.startswith('.'))


@app.get("/api/results/{filename}")
def get_results(filename: str) -> dict:
    """Return the full parsed JSON for a given result file."""
    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    path = PROJECT_ROOT / "results" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"JSON parse error: {exc}")


@app.post("/api/run")
def run_eval(req: RunRequest) -> StreamingResponse:
    """
    Start an eval run and stream stdout/stderr line-by-line as SSE.

    Each event is:  data: {"line": "..."}\n\n
    Final event is: data: {"done": true, "exit_code": N}\n\n
    """
    cmd = [sys.executable, str(PROJECT_ROOT / "run_eval.py")]

    if req.candidate_deployment:
        cmd += ["--candidate-deployment", req.candidate_deployment]
    if req.judge_deployment:
        cmd += ["--judge-deployment", req.judge_deployment]

    cmd += ["--dataset-split",     req.dataset_split]
    cmd += ["--dataset-partition", req.dataset_partition]

    if req.max_samples > 0:
        cmd += ["--max-samples", str(req.max_samples)]

    cmd += ["--max-concurrent", str(req.max_concurrent)]
    cmd += ["--trials",         str(req.trials)]

    # Always route output into the results/ directory unless caller specified a path
    output = req.output
    if output and not Path(output).parent.parts:
        output = f"results/{output}"
    cmd += ["--output", output]

    # Pass temperatures as environment variables
    env = os.environ.copy()
    env["CANDIDATE_TEMPERATURE"] = str(req.candidate_temperature)
    env["JUDGE_TEMPERATURE"]     = str(req.judge_temperature)

    def generate():
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        try:
            for line in process.stdout:
                payload = json.dumps({"line": line.rstrip("\n")})
                yield f"data: {payload}\n\n"
        finally:
            process.wait()
            yield f"data: {json.dumps({'done': True, 'exit_code': process.returncode})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
