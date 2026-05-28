/**
 * EntryDetail
 * Props:
 *   entry   - a single result entry object from the results array
 *   onClose - callback to close / deselect the panel
 */
export default function EntryDetail({ entry, onClose, closeLabel = '✕ Close' }) {
  const pubmedId = entry.pubid ?? '—'
  const question = entry.question ?? ''
  const context = entry.context ?? ''

  // Candidate fields
  const candidateAnswer = entry.candidate?.answer ?? ''
  const candidateReasoning = entry.candidate?.reasoning ?? ''
  const candidateEvidence = entry.candidate?.key_evidence ?? ''

  // Judge fields
  const verdict = entry.judge?.verdict ?? ''
  const labelMatch = entry.judge?.label_match ?? null
  const qualityScore = entry.judge?.quality_score ?? null
  const judgeReasoning = entry.judge?.reasoning ?? ''

  // Gold
  const goldLabel = entry.gold_label ?? ''
  const goldLongAnswer = entry.long_answer ?? ''

  // ---- Helper sub-components ----
  function AnswerBadge({ label }) {
    const l = (label ?? '').toLowerCase()
    const cls =
      l === 'yes' ? 'badge-yes' :
      l === 'no' ? 'badge-no' :
      l === 'maybe' ? 'badge-maybe' :
      'badge-neutral'
    return <span className={`badge ${cls}`}>{l || '—'}</span>
  }

  function VerdictBadge({ v }) {
    const lv = (v ?? '').toLowerCase()
    const cls = lv === 'correct' ? 'badge-correct' : lv === 'incorrect' ? 'badge-incorrect' : 'badge-neutral'
    return <span className={`badge ${cls}`}>{lv || '—'}</span>
  }

  function QualityDisplay({ score }) {
    if (score == null) return <span className="text-muted">N/A</span>
    const n = Number(score)
    const cls = n >= 4 ? 'quality-high' : n >= 3 ? 'quality-mid' : 'quality-low'
    const filled = '★'.repeat(n)
    const empty = '☆'.repeat(5 - n)
    return (
      <span className={`quality-stars ${cls}`}>
        <span className="stars">{filled}{empty}</span>
        &nbsp;{n}/5
      </span>
    )
  }

  return (
    <div className="card entry-detail">
      {/* Header */}
      <div className="entry-detail-header">
        <h3>PubMed ID: {pubmedId}</h3>
        <button className="btn btn-secondary" type="button" onClick={onClose}>
          {closeLabel}
        </button>
      </div>

      {/* Question */}
      <div className="detail-row">
        <div className="detail-label">Question</div>
        <div className="entry-question-box">{question}</div>
      </div>

      {/* Collapsible context */}
      {context && (
        <details>
          <summary>Context / Full Text</summary>
          <div className="details-content">{context}</div>
        </details>
      )}

      {/* Two-column panel: Candidate | Judge */}
      <div className="entry-detail-grid">
        {/* ---- Candidate Response ---- */}
        <div className="detail-section">
          <div className="detail-section-title">Candidate Response</div>

          <div className="detail-row">
            <div className="detail-label">Answer</div>
            <div className="detail-value">
              <AnswerBadge label={candidateAnswer} />
            </div>
          </div>

          {candidateReasoning && (
            <div className="detail-row">
              <div className="detail-label">Reasoning</div>
              <div className="reasoning-block">
                <p>{candidateReasoning}</p>
              </div>
            </div>
          )}

          {candidateEvidence && (
            <div className="detail-row">
              <div className="detail-label">Key Evidence</div>
              <div className="reasoning-block">
                <p>{candidateEvidence}</p>
              </div>
            </div>
          )}

          {!candidateReasoning && !candidateEvidence && (
            <p className="text-muted" style={{ fontSize: '0.8rem' }}>
              No detailed reasoning available.
            </p>
          )}
        </div>

        {/* ---- Judge Evaluation ---- */}
        <div className="detail-section">
          <div className="detail-section-title">Judge Evaluation</div>

          <div className="detail-row">
            <div className="detail-label">Verdict</div>
            <div className="detail-value">
              <VerdictBadge v={verdict} />
            </div>
          </div>

          <div className="detail-row">
            <div className="detail-label">Label Match</div>
            <div className="detail-value">
              {labelMatch == null ? (
                <span className="text-muted">—</span>
              ) : labelMatch ? (
                <span className="match-yes">✓ Match</span>
              ) : (
                <span className="match-no">✗ Mismatch</span>
              )}
            </div>
          </div>

          <div className="detail-row">
            <div className="detail-label">Gold Label</div>
            <div className="detail-value">
              <AnswerBadge label={goldLabel} />
            </div>
          </div>

          <div className="detail-row">
            <div className="detail-label">Quality Score</div>
            <div className="detail-value">
              <QualityDisplay score={qualityScore} />
            </div>
          </div>

          {judgeReasoning && (
            <div className="detail-row">
              <div className="detail-label">Judge Reasoning</div>
              <div className="reasoning-block">
                <p>{judgeReasoning}</p>
              </div>
            </div>
          )}

          {!judgeReasoning && (
            <p className="text-muted" style={{ fontSize: '0.8rem' }}>
              No judge reasoning available.
            </p>
          )}
        </div>
      </div>

      {/* Collapsible gold long answer */}
      {goldLongAnswer && (
        <details>
          <summary>Gold Long Answer</summary>
          <div className="details-content">{goldLongAnswer}</div>
        </details>
      )}
    </div>
  )
}
