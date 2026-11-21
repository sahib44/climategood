import { useState } from 'react'
import { canPostReports, getHealth, getTopicResult, postReport } from '../api.js'
import { formatDate, useAsync } from '../lib.js'

// Report a problem with one statement. The page is opened from that statement's card, so the
// report is already tied to it: the voter only writes what is wrong.
// With a backend that stores reports it is sent there; on the hosted site (which cannot store
// them) it opens the voter's email app with everything filled in. Rule 9: a person checks it.
export default function Report({ candidateId, topicId, statementId }) {
  const result = useAsync(() => getTopicResult(candidateId, topicId), [candidateId, topicId])
  const health = useAsync(getHealth, [])
  const [status, setStatus] = useState(null)
  const card = result.data?.cards.find((c) => c.statement.id === statementId)
  const back = `#/c/${encodeURIComponent(candidateId)}`

  if (result.error) return <main className="page report-page"><p className="notice">Could not load that statement. <a href={back}>Back</a></p></main>
  if (!result.data) return <main className="page report-page"><p className="notice">Loading…</p></main>
  if (!card) return <main className="page report-page"><p className="notice">We could not find that statement. <a href={back}>Back</a></p></main>
  const { statement: s, source } = card
  const name = result.data.candidate.name

  async function onSubmit(e) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const details = [form.get('problem'), form.get('extra')].filter(Boolean).join('\n\n').slice(0, 2000)
    if (canPostReports) {
      setStatus('sending')
      try {
        await postReport({ problem_type: 'other', statement_id: s.id, candidate_id: s.candidate_id, details })
        setStatus('sent')
      } catch {
        setStatus('failed')
      }
      return
    }
    const body = `${details}\n\n---\nStatement: ${s.id}\nCandidate: ${name}\nQuote: “${s.quote_text}”\nVideo: ${s.video_url}`
    window.location.href = `mailto:${health.data?.report_email || ''}?subject=${encodeURIComponent(`Problem with a statement by ${name}`)}&body=${encodeURIComponent(body)}`
    setStatus('emailed')
  }

  return (
    <main className="page report-page">
      <h1>Report a problem</h1>
      <figure className="report-about">
        <blockquote>“{s.quote_text}”</blockquote>
        <figcaption>{name} · {source.publisher} · {formatDate(source.published_date)}</figcaption>
      </figure>

      {status === 'sent' ? (
        <p role="status" className="report-done">Thank you. A person will check this against the original video.</p>
      ) : (
        <form className="report-form" onSubmit={onSubmit}>
          <label>
            What is wrong?
            <textarea name="problem" rows={4} required maxLength={1200} autoFocus />
          </label>
          <label>
            Anything else we should know? <span className="muted">(optional)</span>
            <textarea name="extra" rows={2} maxLength={700} />
          </label>
          <div className="report-actions">
            <button className="button" disabled={status === 'sending'}>Send report</button>
            <a href={back}>Cancel</a>
          </div>
          {status === 'failed' && <p role="alert">Could not send. Please try again.</p>}
          {status === 'emailed' && <p role="status">Your email app should open with the report filled in. Press send there to finish.</p>}
          {!canPostReports && !status && <p className="muted">This opens your email app with the report filled in.</p>}
        </form>
      )}
    </main>
  )
}
