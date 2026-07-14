import { useEffect, useRef, useState } from 'react'
import ActivityFeed from './components/ActivityFeed.jsx'
import ActionPlan from './components/ActionPlan.jsx'
import ChangeLog from './components/ChangeLog.jsx'
import ScoreCard from './components/ScoreCard.jsx'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [url, setUrl] = useState('')
  const [repo, setRepo] = useState('')
  const [events, setEvents] = useState([])
  const [messages, setMessages] = useState([])
  const [state, setState] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const feedRef = useRef(null)

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight
  }, [events])

  async function ensureSession() {
    if (sessionId) return sessionId
    const res = await fetch('/api/session', { method: 'POST' })
    const json = await res.json()
    setSessionId(json.session_id)
    return json.session_id
  }

  async function refreshState(sid) {
    try {
      const res = await fetch(`/api/state/${sid}`)
      if (res.ok) setState(await res.json())
    } catch { /* non-fatal */ }
  }

  /** Send a message and consume the SSE stream of agent events. */
  async function send(message) {
    setRunning(true)
    setError(null)
    const sid = await ensureSession()
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sid, message }),
      })
      if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop()
        for (const chunk of chunks) {
          const line = chunk.replace(/^data: /, '').trim()
          if (!line) continue
          let ev
          try { ev = JSON.parse(line) } catch { continue }
          if (ev.type === 'error') setError(ev.message)
          else if (ev.type === 'message' && ev.final) {
            setMessages((m) => [...m, { agent: ev.agent, text: ev.text }])
          } else if (ev.type !== 'done') {
            setEvents((e) => [...e, ev])
          }
        }
      }
    } catch (e) {
      setError(String(e.message || e))
    } finally {
      setRunning(false)
      await refreshState(sid)
    }
  }

  function runAnalysis(e) {
    e.preventDefault()
    if (!url.trim() || running) return
    setEvents([]); setMessages([]); setState(null)
    send(`Analyze ${url.trim()} and run the Phase 1 diagnosis. I approve the analysis.`)
  }

  function approve(section) {
    if (running) return
    const repoPart = repo.trim() ? ` Here is the repo: ${repo.trim()}` : ''
    const focus = section && section !== 'all' ? ` Focus on ${section} first.` : ''
    send(`approve.${focus}${repoPart}`)
  }

  const hasPlan = Boolean(state?.action_plan) || messages.length > 0

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>SEO + AEO Agent</h1>
          <p className="sub">Analyze → plan → implement, grounded and gated.</p>
        </div>
        {state?.project_brief?.niche && (
          <div className="badge">niche: {state.project_brief.niche}</div>
        )}
      </header>

      <form className="urlbar" onSubmit={runAnalysis}>
        <input
          type="url"
          placeholder="https://your-site.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={running}
        />
        <button type="submit" disabled={running || !url.trim()}>
          {running ? 'Working…' : 'Run Analysis'}
        </button>
      </form>

      {error && <div className="error">⚠ {error}</div>}

      <div className="grid">
        <section className="col">
          <h2>Activity</h2>
          <div className="feed" ref={feedRef}>
            <ActivityFeed events={events} running={running} />
          </div>
        </section>

        <section className="col">
          <h2>Health Score</h2>
          <ScoreCard card={state?.scorecard_baseline} after={state?.scorecard_after} />
        </section>
      </div>

      {hasPlan && (
        <section className="panel">
          <h2>Action Plan</h2>
          <ActionPlan text={state?.action_plan} messages={messages} />
          <div className="approve">
            <input
              type="text"
              placeholder="Optional: git repo URL to apply changes (https://github.com/you/site.git)"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              disabled={running}
            />
            <div className="actions">
              <button onClick={() => approve('all')} disabled={running}>
                Approve &amp; Implement
              </button>
              {['technical', 'on-page', 'content', 'off-page', 'AEO'].map((s) => (
                <button key={s} className="ghost" onClick={() => approve(s)} disabled={running}>
                  Focus: {s}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {state?.change_log?.length > 0 && (
        <section className="panel">
          <h2>Changes Applied</h2>
          <ChangeLog log={state.change_log} siteType={state.site_type} />
        </section>
      )}
    </div>
  )
}
