import { useState, useEffect } from 'react'
import { fetchFiles, fetchResults } from '../api.js'
import EntryDetail from '../components/EntryDetail.jsx'

const DEFAULT_FILTERS = {
  goldLabels: ['yes', 'no', 'maybe'],
  verdicts: ['correct', 'incorrect'],
  statuses: ['success', 'candidate_error', 'judge_error'],
  minQuality: 1,
}

function computeSummaryMetrics(results) {
  if (!results || results.length === 0) {
    return { accuracy: 0, total: 0, avgQuality: 0, correct: 0, incorrect: 0 }
  }
  const judged = results.filter((r) => r.verdict != null)
  const correct = judged.filter((r) => r.verdict === 'correct').length
  const incorrect = judged.filter((r) => r.verdict === 'incorrect').length
  const accuracy = judged.length > 0 ? ((correct / judged.length) * 100).toFixed(1) : '0.0'
  const qualityScores = results
    .map((r) => r.quality_score ?? r.qualityScore)
    .filter((q) => q != null && !isNaN(q))
  const avgQuality =
    qualityScores.length > 0
      ? (qualityScores.reduce((a, b) => a + b, 0) / qualityScores.length).toFixed(2)
      : 'N/A'
  return { accuracy, total: judged.length, avgQuality, correct, incorrect }
}

function getLabel(entry, field, ...fallbacks) {
  if (entry[field] != null) return entry[field]
  for (const f of fallbacks) {
    if (entry[f] != null) return entry[f]
  }
  return null
}

export default function ViewResults() {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [selectedEntryIndex, setSelectedEntryIndex] = useState(null)

  // Load file list on mount
  useEffect(() => {
    loadFiles()
  }, [])

  // Fetch results when selectedFile changes
  useEffect(() => {
    if (!selectedFile) {
      setData(null)
      setSelectedEntryIndex(null)
      return
    }
    setLoading(true)
    setError(null)
    setSelectedEntryIndex(null)
    fetchResults(selectedFile)
      .then((d) => {
        setData(d)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [selectedFile])

  async function loadFiles() {
    try {
      const list = await fetchFiles()
      setFiles(Array.isArray(list) ? list : [])
    } catch {
      setFiles([])
    }
  }

  function toggleFilter(key, value) {
    setFilters((prev) => {
      const current = prev[key]
      const next = current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value]
      return { ...prev, [key]: next }
    })
    setSelectedEntryIndex(null)
  }

  function setMinQuality(val) {
    setFilters((prev) => ({ ...prev, minQuality: Number(val) }))
    setSelectedEntryIndex(null)
  }

  const allResults = data?.results ?? []

  const filteredResults = allResults.filter((entry) => {
    const gold = getLabel(entry, 'gold_label', 'goldLabel', 'gold') ?? ''
    const verdict = getLabel(entry, 'verdict') ?? ''
    const status = getLabel(entry, 'status') ?? 'success'
    const quality = getLabel(entry, 'quality_score', 'qualityScore') ?? 1

    if (!filters.goldLabels.includes(gold.toLowerCase())) return false
    if (verdict && !filters.verdicts.includes(verdict.toLowerCase())) return false
    if (!filters.statuses.includes(status.toLowerCase())) return false
    if (quality < filters.minQuality) return false
    return true
  })

  const metrics = computeSummaryMetrics(allResults)

  function truncate(str, len = 80) {
    if (!str) return ''
    return str.length > len ? str.slice(0, len) + '…' : str
  }

  function GoldBadge({ label }) {
    const l = (label ?? '').toLowerCase()
    const cls = l === 'yes' ? 'badge-yes' : l === 'no' ? 'badge-no' : 'badge-maybe'
    return <span className={`badge ${cls}`}>{l || '—'}</span>
  }

  function VerdictBadge({ verdict }) {
    const v = (verdict ?? '').toLowerCase()
    const cls = v === 'correct' ? 'badge-correct' : v === 'incorrect' ? 'badge-incorrect' : 'badge-neutral'
    return <span className={`badge ${cls}`}>{v || '—'}</span>
  }

  function QualityDisplay({ score }) {
    if (score == null) return <span className="text-muted">—</span>
    const n = Number(score)
    const cls = n >= 4 ? 'quality-high' : n >= 3 ? 'quality-mid' : 'quality-low'
    return <span className={`quality-stars ${cls}`}>{n}/5</span>
  }

  return (
    <>
      <div className="page-header">
        <h1>View Results</h1>
        <p className="page-subtitle">Browse and analyze evaluation outputs</p>
      </div>

      {/* File selector */}
      <div className="card">
        <div className="select-file">
          <label htmlFor="file-select">Result File</label>
          <select
            id="file-select"
            value={selectedFile ?? ''}
            onChange={(e) => setSelectedFile(e.target.value || null)}
          >
            <option value="">— Select a file —</option>
            {files.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
          <button
            className="btn btn-secondary"
            type="button"
            onClick={loadFiles}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* No files message */}
      {files.length === 0 && !loading && (
        <div className="empty-state">
          <span className="empty-icon">📂</span>
          No result files found. Run an evaluation first.
        </div>
      )}

      {/* Loading indicator */}
      {loading && (
        <div className="empty-state">
          <span className="empty-icon">⏳</span>
          Loading results…
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="status-bar status-error" style={{ marginBottom: '1rem' }}>
          ✗ {error}
        </div>
      )}

      {/* Results area */}
      {!loading && data && (
        <>
          {/* Metrics grid */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-value accent">{metrics.accuracy}%</div>
              <div className="metric-label">Accuracy</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.total}</div>
              <div className="metric-label">Total Judged</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{metrics.avgQuality}</div>
              <div className="metric-label">Avg Quality Score</div>
            </div>
            <div className="metric-card">
              <div className="metric-value success">{metrics.correct}</div>
              <div className="metric-label">
                Correct / <span style={{ color: 'var(--color-danger)' }}>{metrics.incorrect}</span> Incorrect
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="filters-row">
            <div className="filter-group">
              <label>Gold Label</label>
              <div className="filter-checkboxes">
                {['yes', 'no', 'maybe'].map((v) => (
                  <label key={v}>
                    <input
                      type="checkbox"
                      checked={filters.goldLabels.includes(v)}
                      onChange={() => toggleFilter('goldLabels', v)}
                    />
                    {v}
                  </label>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <label>Verdict</label>
              <div className="filter-checkboxes">
                {['correct', 'incorrect'].map((v) => (
                  <label key={v}>
                    <input
                      type="checkbox"
                      checked={filters.verdicts.includes(v)}
                      onChange={() => toggleFilter('verdicts', v)}
                    />
                    {v}
                  </label>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <label>Status</label>
              <div className="filter-checkboxes">
                {['success', 'candidate_error', 'judge_error'].map((v) => (
                  <label key={v}>
                    <input
                      type="checkbox"
                      checked={filters.statuses.includes(v)}
                      onChange={() => toggleFilter('statuses', v)}
                    />
                    {v}
                  </label>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <label>Min Quality: {filters.minQuality}</label>
              <input
                type="range"
                min="1"
                max="5"
                step="1"
                value={filters.minQuality}
                onChange={(e) => setMinQuality(e.target.value)}
              />
            </div>
          </div>

          <p className="results-count">
            Showing {filteredResults.length} of {allResults.length} results
          </p>

          {/* Table */}
          {filteredResults.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">🔍</span>
              No results match the current filters.
            </div>
          ) : (
            <div className="results-table-wrapper">
              <table className="results-table">
                <thead>
                  <tr>
                    <th className="col-num">#</th>
                    <th>PubMed ID</th>
                    <th>Question</th>
                    <th>Gold</th>
                    <th>Candidate</th>
                    <th>Match</th>
                    <th>Verdict</th>
                    <th>Quality</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResults.map((entry, idx) => {
                    const pubmedId =
                      getLabel(entry, 'pubmed_id', 'pubmedId', 'pmid') ?? '—'
                    const question =
                      getLabel(entry, 'question') ?? ''
                    const gold =
                      getLabel(entry, 'gold_label', 'goldLabel', 'gold') ?? ''
                    const candidateAnswer =
                      getLabel(entry, 'candidate_answer', 'candidateAnswer') ?? ''
                    const verdict =
                      getLabel(entry, 'verdict') ?? ''
                    const quality =
                      getLabel(entry, 'quality_score', 'qualityScore')
                    const labelMatch =
                      getLabel(entry, 'label_match', 'labelMatch')

                    const isSelected = selectedEntryIndex === idx

                    return (
                      <tr
                        key={idx}
                        className={isSelected ? 'row-selected' : ''}
                        onClick={() =>
                          setSelectedEntryIndex(isSelected ? null : idx)
                        }
                      >
                        <td className="col-num">{idx + 1}</td>
                        <td>{pubmedId}</td>
                        <td className="col-question">
                          <span className="question-text" title={question}>
                            {truncate(question, 80)}
                          </span>
                        </td>
                        <td>
                          <GoldBadge label={gold} />
                        </td>
                        <td>
                          <GoldBadge label={candidateAnswer} />
                        </td>
                        <td>
                          {labelMatch == null ? (
                            <span className="text-muted">—</span>
                          ) : labelMatch ? (
                            <span className="match-yes">✓</span>
                          ) : (
                            <span className="match-no">✗</span>
                          )}
                        </td>
                        <td>
                          <VerdictBadge verdict={verdict} />
                        </td>
                        <td>
                          <QualityDisplay score={quality} />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Entry detail panel */}
          {selectedEntryIndex !== null && filteredResults[selectedEntryIndex] && (
            <EntryDetail
              entry={filteredResults[selectedEntryIndex]}
              onClose={() => setSelectedEntryIndex(null)}
            />
          )}
        </>
      )}
    </>
  )
}
