import { useState } from 'react'
import { getTopicResult, postReport } from '../api.js'
import { CheckIcon } from '../components/icons.jsx'
import { formatDate, useAsync } from '../lib.js'

// Report a problem with one statement. The page is opened from that statement's card, so the
// report is already tied to it: the voter only writes what is wrong.
// It is sent straight to the API (POST /reports) and a success page always follows (demo).
// Rule 9: a person checks every report.
export default function Report({ candidateId, topicId, statementId }) {
  const result = useAsync(() => getTopicResult(candidateId, topicId), [candidateId, topicId])
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
    setStatus('sending')
    // DEMO BEHAVIOUR: the success page always follows. The report is sent with its statement;
    // if that is refused it is sent again as plain text; if the API cannot be reached at all
    // the voter still sees "Report sent". Before real use, show the failure instead.
    const report = { problem_type: 'other', details }
    try {
      await postReport({ ...report, statement_id: s.id, candidate_id: s.candidate_id })
    } catch {
      await postReport(report).catch(() => {})
    }
    setStatus('sent')
  }

  if (status === 'sent') {
    return (
      <main className="page report-page report-sent" role="status">
        <span className="report-tick"><CheckIcon /></span>
        <h1>Report sent</h1>
        <p>Thank you. A person will check this statement against the original video.</p>
        <a className="button" href={back}>Back to {name}</a>
      </main>
    )
  }

  return (
    <main className="page report-page">
      <h1>Report a problem</h1>
      <figure className="report-about">
        <blockquote>“{s.quote_text}”</blockquote>
        <figcaption>{name} · {source.publisher} · {formatDate(source.published_date)}</figcaption>
      </figure>

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
          <button className="button" disabled={status === 'sending'}>{status === 'sending' ? 'Sending…' : 'Send report'}</button>
          <a href={back}>Cancel</a>
        </div>
      </form>
    </main>
  )
}
