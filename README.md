# PubMedQA Eval Harness

An evaluation pipeline that uses one LLM (candidate) to answer PubMedQA questions and a separate LLM (judge) to evaluate the responses.

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the `.env` file and fill in your values:

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.services.ai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=<your-api-key>
CANDIDATE_DEPLOYMENT=<deployment-name>
JUDGE_DEPLOYMENT=<deployment-name>
```

---

## Running the eval harness (CLI)

```bash
# Run 3 trials on 50 samples
python run_eval.py --trials 3 --max-samples 50

# Run on a specific subset
python run_eval.py --dataset-subset reasoning_required --max-samples 100

# Full run, all samples
python run_eval.py --trials 1
```

Results are saved as `eval_results_<candidate>_judge-<judge>.json` (or `_1.json`, `_2.json` etc. for multiple trials).

### Browse results in the terminal

```bash
python view.py                    # interactive file + entry picker
python view.py --trial 2          # open trial 2 directly
python view.py --verdict incorrect # random incorrect entry
```

---

## Running the dashboard (React + FastAPI)

The dashboard lets you run trials and explore results from a browser.

### 1. Start the backend

```bash
uvicorn api:app --reload --port 8000
```

### 2. Install frontend dependencies (first time only)

```bash
cd frontend
npm install
```

### 3. Start the frontend

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

The **Run Trials** page lets you configure and launch eval runs with live log output.  
The **View Results** page lets you explore result files with filters and per-entry detail.

---

## File structure

| File | Purpose |
|---|---|
| `utils.py` | Config, data models, prompt templates |
| `dataset.py` | PubMedQA loader |
| `candidate.py` | Candidate model logic |
| `judge.py` | Judge model logic |
| `evaluator.py` | Async eval loop |
| `report.py` | JSON report writer |
| `run_eval.py` | CLI entrypoint |
| `view.py` | Terminal result browser |
| `api.py` | FastAPI backend for the dashboard |
| `frontend/` | React + Vite dashboard |
