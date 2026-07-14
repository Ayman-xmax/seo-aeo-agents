const STATUS_CLASS = {
  success: 'ok',
  applied_to_file: 'ok',
  applied_to_cms: 'ok',
  committed: 'ok',
  recorded_changeset: 'warn',
  not_configured: 'warn',
  unavailable: 'warn',
  not_found: 'warn',
  blocked_awaiting_approval: 'warn',
  error: 'bad',
}

export default function ActivityFeed({ events, running }) {
  if (!events.length) {
    return (
      <p className="muted">
        {running ? 'Starting…' : 'Enter your site URL and run the analysis. The agent reads your site, infers the niche, and audits it.'}
      </p>
    )
  }
  return (
    <ul className="events">
      {events.map((ev, i) => (
        <li key={i} className="event">
          <span className="agent">{ev.agent}</span>
          {ev.type === 'tool_call' && (
            <>
              <span className="arrow">→</span>
              <code>{ev.tool}</code>
            </>
          )}
          {ev.type === 'tool_result' && (
            <>
              <span className="arrow">←</span>
              <code>{ev.tool}</code>
              {ev.status && (
                <span className={`status ${STATUS_CLASS[ev.status] || ''}`}>{ev.status}</span>
              )}
            </>
          )}
          {ev.type === 'message' && <span className="say">{ev.text.slice(0, 160)}</span>}
        </li>
      ))}
      {running && <li className="event muted">working…</li>}
    </ul>
  )
}
