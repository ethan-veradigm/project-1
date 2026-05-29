import { useState, useEffect, useRef } from 'react'
import { fetchConfig, startRun } from '../api.js'

const DEFAULT_FORM = {
  candidateDeployment: '',
  judgeDeployment: '',
  datasetSplit: 'pqa_labeled',
  datasetPartition: 'test',
  maxSamples: 0,
  maxConcurrent: 5,
  trials: 1,
  output: '',
  candidateTemperature: 0.0,
  judgeTemperature: 0.0,
}

const DEPLOYMENTS = ['gpt-5.4-mini', 'gpt-5.5']
const FORCED_TEMP_DEPLOYMENT = 'gpt-5.5'
const PROGRESS_RE = /^PROGRESS:(\d+)\/(\d+)$/

export default function RunTrials() {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [running, setRunning] = useState(false)
  const [logLines, setLogLines] = useState([])
  const [exitCode, setExitCode] = useState(null)
  const [progress, setProgress] = useState(null) // { done: N, total: M } | null
  const logRef = useRef(null)

  // Pre-fill form from backend config on mount
  useEffect(() => {
    fetchConfig()
      .then((cfg) => {
        setForm((prev) => ({
          ...prev,
          ...(cfg.candidate_deployment != null && { candidateDeployment: cfg.candidate_deployment }),
          ...(cfg.judge_deployment != null && { judgeDeployment: cfg.judge_deployment }),
          ...(cfg.dataset_split != null && { datasetSplit: cfg.dataset_split }),
          ...(cfg.dataset_partition != null && { datasetPartition: cfg.dataset_partition }),
          ...(cfg.max_samples != null && { maxSamples: cfg.max_samples }),
          ...(cfg.max_concurrent != null && { maxConcurrent: cfg.max_concurrent }),
          ...(cfg.trials != null && { trials: cfg.trials }),
          ...(cfg.output != null && { output: cfg.output }),
          ...(cfg.candidate_temperature != null && { candidateTemperature: cfg.candidate_temperature }),
          ...(cfg.judge_temperature != null && { judgeTemperature: cfg.judge_temperature }),
        }))
      })
      .catch(() => {
        // Config endpoint may not exist yet; use defaults
      })
  }, [])

  // Auto-scroll log to bottom whenever lines change
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logLines])

  function handleChange(e) {
    const { name, value, type } = e.target
    setForm((prev) => {
      const updated = { ...prev, [name]: type === 'number' ? Number(value) : value }
      if (name === 'candidateDeployment' && value === FORCED_TEMP_DEPLOYMENT)
        updated.candidateTemperature = 1
      if (name === 'judgeDeployment' && value === FORCED_TEMP_DEPLOYMENT)
        updated.judgeTemperature = 1
      return updated
    })
  }

  async function handleRun(e) {
    e.preventDefault()
    setLogLines([])
    setExitCode(null)
    setProgress(null)
    setRunning(true)

    const config = {
      candidate_deployment: form.candidateDeployment,
      judge_deployment: form.judgeDeployment,
      dataset_split: form.datasetSplit,
      dataset_partition: form.datasetPartition,
      max_samples: form.maxSamples,
      max_concurrent: form.maxConcurrent,
      trials: form.trials,
      output: form.output,
      candidate_temperature: form.candidateTemperature,
      judge_temperature: form.judgeTemperature,
    }

    try {
      await startRun(
        config,
        (line) => {
          const m = PROGRESS_RE.exec(line)
          if (m) {
            setProgress({ done: Number(m[1]), total: Number(m[2]) })
          } else {
            setLogLines((prev) => [...prev, line])
          }
        },
        (code) => {
          setExitCode(code)
          setRunning(false)
        }
      )
    } catch (err) {
      setLogLines((prev) => [...prev, `[ERROR] ${err.message}`])
      setExitCode(1)
      setRunning(false)
    }
  }

  const summaryLines = (() => {
    const idx = logLines.findIndex((l) => l.startsWith('==='))
    return idx === -1 ? [] : logLines.slice(idx)
  })()

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Run Trials</h1>
          <p className="page-subtitle">Configure and launch evaluation runs</p>
        </div>
      </div>

      <div className="card">
        <form onSubmit={handleRun}>
          <div className="form-grid">
            {/* ---- Left column ---- */}
            <div className="form-group">
              <label htmlFor="candidateDeployment">Candidate Deployment</label>
              <select
                id="candidateDeployment"
                name="candidateDeployment"
                value={form.candidateDeployment}
                onChange={handleChange}
                required
              >
                <option value="">— Select —</option>
                {DEPLOYMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="judgeDeployment">Judge Deployment</label>
              <select
                id="judgeDeployment"
                name="judgeDeployment"
                value={form.judgeDeployment}
                onChange={handleChange}
                required
              >
                <option value="">— Select —</option>
                {DEPLOYMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="candidateTemperature">
                Candidate Temperature
                {form.candidateDeployment === FORCED_TEMP_DEPLOYMENT && (
                  <span className="forced-temp-note"> (locked to 1)</span>
                )}
              </label>
              <input
                id="candidateTemperature"
                name="candidateTemperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={form.candidateTemperature}
                onChange={handleChange}
                disabled={form.candidateDeployment === FORCED_TEMP_DEPLOYMENT}
              />
            </div>

            <div className="form-group">
              <label htmlFor="judgeTemperature">
                Judge Temperature
                {form.judgeDeployment === FORCED_TEMP_DEPLOYMENT && (
                  <span className="forced-temp-note"> (locked to 1)</span>
                )}
              </label>
              <input
                id="judgeTemperature"
                name="judgeTemperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={form.judgeTemperature}
                onChange={handleChange}
                disabled={form.judgeDeployment === FORCED_TEMP_DEPLOYMENT}
              />
            </div>

            {/* ---- Right column (second grid column) ---- */}
            <div className="form-group">
              <label htmlFor="datasetSplit">Dataset Split</label>
              <select
                id="datasetSplit"
                name="datasetSplit"
                value={form.datasetSplit}
                onChange={handleChange}
              >
                <option value="pqa_labeled">pqa_labeled</option>
                <option value="pqa_artificial">pqa_artificial</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="datasetPartition">Dataset Partition</label>
              <select
                id="datasetPartition"
                name="datasetPartition"
                value={form.datasetPartition}
                onChange={handleChange}
              >
                <option value="train">train</option>
                <option value="test">test</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="maxSamples">Max Samples (0 = all)</label>
              <input
                id="maxSamples"
                name="maxSamples"
                type="number"
                min="0"
                step="1"
                value={form.maxSamples}
                onChange={handleChange}
              />
            </div>

            {/* ---- Full-width row ---- */}
            <div className="form-group full-width">
              <label htmlFor="trials">Trials per Sample</label>
              <input
                id="trials"
                name="trials"
                type="number"
                min="1"
                step="1"
                value={form.trials}
                onChange={handleChange}
              />
            </div>

            <div className="form-group full-width">
              <label htmlFor="maxConcurrent">Max Concurrent Requests</label>
              <input
                id="maxConcurrent"
                name="maxConcurrent"
                type="number"
                min="1"
                step="1"
                value={form.maxConcurrent}
                onChange={handleChange}
              />
            </div>

            <div className="form-group full-width">
              <label htmlFor="output">Output File Path</label>
              <input
                id="output"
                name="output"
                type="text"
                value={form.output}
                onChange={handleChange}
                placeholder=""
                required
              />
            </div>
          </div>

          <div style={{ marginTop: '1.25rem' }}>
            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={running}
            >
              {running ? (
                <>
                  <span className="spinner" />
                  Running…
                </>
              ) : (
                '▶ Run Evaluation'
              )}
            </button>
          </div>
        </form>
      </div>

      {(running || progress !== null || logLines.length > 0) && (
        <div className="card" style={{ padding: '1rem' }}>
          <div className="card-title" style={{ marginBottom: '0.75rem' }}>
            {exitCode === null ? 'Running…' : 'Results'}
          </div>

          {progress !== null && (
            <div className="progress-wrap">
              <div className="progress-header">
                <span>Evaluating samples</span>
                <span className="progress-count">
                  {progress.done} / {progress.total}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${(progress.done / progress.total) * 100}%` }}
                />
              </div>
              <div className="progress-pct">
                {((progress.done / progress.total) * 100).toFixed(0)}%
              </div>
            </div>
          )}

          {exitCode !== null && summaryLines.length > 0 && (
            <div className="log-output" ref={logRef}>
              {summaryLines.join('\n')}
            </div>
          )}

          {exitCode !== null && (
            <div
              className={`status-bar ${exitCode === 0 ? 'status-success' : 'status-error'}`}
            >
              {exitCode === 0
                ? '✓ Evaluation completed successfully.'
                : `✗ Evaluation exited with code ${exitCode}.`}
            </div>
          )}
        </div>
      )}
    </>
  )
}
