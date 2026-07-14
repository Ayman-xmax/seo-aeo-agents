/**
 * The action plan is written by the agent as readable text (with exact
 * current -> new values). Render it verbatim; fall back to the last agent
 * messages if the plan isn't in state yet.
 */
export default function ActionPlan({ text, messages }) {
  const body = text || messages.map((m) => m.text).join('\n\n')
  if (!body?.trim()) return <p className="muted">No plan yet.</p>
  return <pre className="plan">{body}</pre>
}
