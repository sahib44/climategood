import { useState } from 'react'
import { canPostReports, postReport } from '../api.js'
import { formatDate, formatTime, urlAtTime } from '../lib.js'
import { ArrowUpRightIcon, CheckIcon, PlayIcon } from './icons.jsx'
import Label from './Label.jsx'

const METHOD = {
  exact_normalized: 'The quote matches the transcript exactly (ignoring case and punctuation).',
  near_exact: 'The quote matches the transcript almost exactly. The text shown is the transcript’s.',
}

// The same card for every candidate (rule 1). The quote is the transcript text from the API,
// shown as-is: never trimmed, reworded or summarized here (rule 2).
export default function ClipCard({ card, reportEmail }) {
  const { statement: s, source } = card
  return (
    <li className="clip">
      <time className="clip-date" dateTime={source.published_date}>{formatDate(source.published_date)}</time>
      <article className="card clip-card">
        <blockquote>“{s.quote_text}”</blockquote>

        <p className="clip-labels">
          <span className="verified" title={METHOD[s.verification_method]}>
            <CheckIcon /> Verified against transcript
          </span>
          <Label>quote: {s.label}</Label>
          <Label>topic match: {s.topic_match_label}</Label>
        </p>

        <p className="clip-source muted">
          {source.venue} · Publisher: {source.publisher} · {source.title} ·{' '}
          <a className="icon-link" href={source.url} target="_blank" rel="noreferrer">View original source <ArrowUpRightIcon /></a>
        </p>

        <div className="clip-actions">
          <a className="button" href={urlAtTime(s.video_url, s.start_sec)} target="_blank" rel="noreferrer">
            <PlayIcon /> Watch at {formatTime(s.start_sec)}
          </a>
          <details className="context">
            <summary>Show context (what was said before and after)</summary>
            <p>
              {s.context_before && <span className="muted">{s.context_before} </span>}
              <mark>{s.quote_text}</mark>
              {s.context_after && <span className="muted"> {s.context_after}</span>}
            </p>
          </details>
        </div>

        <Report statement={s} reportEmail={reportEmail} />
      </article>
    </li>
  )
}

const PROBLEMS = [
  ['wrong_quote', 'The quote is wrong'],
  ['wrong_timestamp', 'The timestamp is wrong'],
  ['misattributed', 'Someone else said this'],
  ['edited_clip', 'The clip looks edited'],
  ['missing_statement', 'A statement is missing'],
  ['other', 'Something else'],
]

// Rule 9: mailto always works; the form posts to /reports when a backend is connected.
function Report({ statement, reportEmail }) {
  const [status, setStatus] = useState(null)
  const mailto = reportEmail
    ? `mailto:${reportEmail}?subject=${encodeURIComponent(`Firsthand problem report: ${statement.id}`)}`
    : null

  async function onSubmit(e) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    setStatus('sending')
    try {
      await postReport({
        problem_type: form.get('problem_type'),
        statement_id: statement.id,
        candidate_id: statement.candidate_id,
        details: form.get('details'),
      })
      setStatus('sent')
    } catch {
      setStatus('failed')
    }
  }

  return (
    <details className="report">
      <summary>Report a problem</summary>
      {mailto && <p>Email us: <a href={mailto}>{reportEmail}</a>. A person checks every report against the original source.</p>}
      {canPostReports && status !== 'sent' && (
        <form onSubmit={onSubmit}>
          <select name="problem_type" aria-label="What is wrong?" defaultValue="wrong_quote">
            {PROBLEMS.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
          </select>
          <textarea name="details" maxLength={2000} rows={2} placeholder="Details (optional)" aria-label="Details" />
          <button className="button button-quiet" disabled={status === 'sending'}>Send report</button>
          {status === 'failed' && <span role="alert"> Could not send. Please use the email link.</span>}
        </form>
      )}
      {status === 'sent' && <p role="status">Report received. A person will check the original source.</p>}
    </details>
  )
}
