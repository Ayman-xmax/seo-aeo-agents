const LABELS = {
  technical: 'Technical',
  on_page: 'On-Page',
  content_keyword: 'Content & Keyword',
  off_page: 'Off-Page',
  aeo_geo: 'AEO / GEO',
}

function tone(score) {
  if (typeof score !== 'number') return 'na'
  if (score >= 80) return 'good'
  if (score >= 55) return 'mid'
  return 'poor'
}

export default function ScoreCard({ card, after }) {
  if (!card) {
    return <p className="muted">No score yet — run an analysis to get a deterministic 5-category Health Score.</p>
  }
  const overall = card.overall
  return (
    <div className="score">
      <div className="overall">
        <div className={`big ${tone(overall)}`}>{overall ?? '—'}</div>
        <div className="overall-meta">
          <span>Overall</span>
          <span className="muted">coverage {card.coverage ?? '—'}</span>
          {after?.overall != null && (
            <span className="delta">after: {after.overall}</span>
          )}
        </div>
      </div>

      <ul className="cats">
        {(card.categories || []).map((c) => {
          const numeric = typeof c.score === 'number'
          return (
            <li key={c.category}>
              <div className="cat-head">
                <span>{LABELS[c.category] || c.category}</span>
                <span className={`val ${tone(c.score)}`}>
                  {numeric ? c.score : 'insufficient data'}
                </span>
              </div>
              <div className="bar">
                <div
                  className={`fill ${tone(c.score)}`}
                  style={{ width: numeric ? `${Math.max(2, c.score)}%` : '0%' }}
                />
              </div>
              {c.notes?.length > 0 && <p className="note">{c.notes[0]}</p>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
