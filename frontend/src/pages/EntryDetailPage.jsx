import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchResults } from '../api.js'
import EntryDetail from '../components/EntryDetail.jsx'

export default function EntryDetailPage() {
  const { filename, index } = useParams()
  const navigate = useNavigate()
  const [entry, setEntry] = useState(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const idx = Number(index)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchResults(filename)
      .then((data) => {
        const results = data?.results ?? []
        setTotal(results.length)
        if (idx < 0 || idx >= results.length) {
          setError(`Entry ${idx + 1} not found in ${filename}.`)
        } else {
          setEntry(results[idx])
        }
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [filename, idx])

  function goTo(newIdx) {
    navigate(`/results/${encodeURIComponent(filename)}/${newIdx}`)
  }

  return (
    <>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => navigate(`/results?file=${encodeURIComponent(filename)}`)}
          >
            ← Back to Results
          </button>
          <div>
            <h1 style={{ margin: 0 }}>Entry Detail</h1>
            <p className="page-subtitle" style={{ margin: 0 }}>
              {filename} — entry {idx + 1}{total > 0 ? ` of ${total}` : ''}
            </p>
          </div>
        </div>

        {total > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary"
              type="button"
              disabled={idx === 0}
              onClick={() => goTo(idx - 1)}
            >
              ← Prev
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              disabled={idx >= total - 1}
              onClick={() => goTo(idx + 1)}
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {loading && (
        <div className="empty-state">
          <span className="empty-icon">⏳</span>
          Loading entry…
        </div>
      )}

      {error && (
        <div className="status-bar status-error" style={{ marginBottom: '1rem' }}>
          ✗ {error}
        </div>
      )}

      {!loading && entry && (
        <EntryDetail entry={entry} onClose={() => navigate(`/results?file=${encodeURIComponent(filename)}`)} />
      )}
    </>
  )
}
