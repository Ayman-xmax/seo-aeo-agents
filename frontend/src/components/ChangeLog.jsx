const OK = new Set(['applied_to_file', 'applied_to_cms', 'committed', 'pushed'])

export default function ChangeLog({ log, siteType }) {
  return (
    <>
      {siteType && <p className="muted">Detected site type: <code>{siteType}</code></p>}
      <table className="log">
        <thead>
          <tr><th>Target</th><th>Field</th><th>New value</th><th>Result</th></tr>
        </thead>
        <tbody>
          {log.map((c, i) => (
            <tr key={i}>
              <td><code>{c.target}</code></td>
              <td>{c.field}</td>
              <td className="val-cell">{c.value_preview || '—'}</td>
              <td>
                <span className={`status ${OK.has(c.result_status) ? 'ok' : 'warn'}`}>
                  {c.result_status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
