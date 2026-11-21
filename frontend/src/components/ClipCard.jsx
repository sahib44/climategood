import { useState } from 'react'
import { canPostReports, postReport } from '../api.js'
import { embedAtTime, formatDate, formatTime, thumbnailFor, urlAtTime } from '../lib.js'
import { ArrowUpRightIcon, CalendarIcon, ChevronIcon, FlagIcon, PinIcon, PlayIcon, TopicIcon, TvIcon, VerifiedIcon } from './icons.jsx'
import Label from './Label.jsx'

const METHOD = {
  exact_normalized: 'The quote matches the transcript exactly (ignoring case and punctuation).',
  near_exact: 'The quote matches the transcript almost exactly. The text shown is the transcript’s.',
}

// The same card for every candidate (rule 1). The quote is the transcript text from the API,
// shown as-is: never trimmed, reworded or summarized here (rule 2).
export default function ClipCard({ card, topic, reportEmail }) {
  const { statement: s, source } = card
  const [playing, setPlaying] = useState(false)
  const embed = embedAtTime(s.video_url, s.start_sec)
  const thumb = thumbnailFor(s.video_url)
  const venue = /not stated/i.test(source.venue || '') ? null : source.venue
  const tile = (
    <>
      {thumb && <img src={thumb} alt="" loading="lazy" />}
      <span className="clip-play-button"><PlayIcon /></span>
      <span className="clip-time">{formatTime(s.start_sec)}</span>
    </>
  )
  return (
    <li className="clip">
      <article className="card clip-card">
        {/* Rule 3: the publisher's own player, loaded only when the voter presses play. */}
        {playing && embed ? (
          <iframe className="clip-video" src={embed} title={`${source.publisher}: ${source.title}`}
            allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen />
        ) : embed ? (
          <button type="button" className="clip-play" onClick={() => setPlaying(true)}
            aria-label={`Play the video at ${formatTime(s.start_sec)}`}>{tile}</button>
        ) : (
          <a className="clip-play" href={urlAtTime(s.video_url, s.start_sec)} target="_blank" rel="noreferrer"
            aria-label={`Watch the video at ${formatTime(s.start_sec)}`}>{tile}</a>
        )}

        <div className="clip-body">
          {topic && <span className="topic-tag"><TopicIcon id={topic.id} size={14} /> {topic.label}</span>}
          <blockquote>“{s.quote_text}”</blockquote>

          <p className="clip-source">
            <span><CalendarIcon /> <time dateTime={source.published_date}>{formatDate(source.published_date)}</time></span>
            <span><TvIcon /> {source.publisher}</span>
            {venue && <span><PinIcon /> {venue}</span>}
          </p>
          <p className="clip-title">{source.title}</p>

          <p className="clip-labels">
            <span className="verified" title={METHOD[s.verification_method]}><VerifiedIcon /> Verified against transcript</span>
            <Label>quote: {s.label}</Label>
            <Label>topic match: {s.topic_match_label}</Label>
          </p>

          <div className="clip-links">
            <details className="context">
              <summary>Context <ChevronIcon /></summary>
              <p>
                {s.context_before && <span className="muted">{s.context_before} </span>}
                <mark>{s.quote_text}</mark>
                {s.context_after && <span className="muted"> {s.context_after}</span>}
              </p>
            </details>
            <a className="icon-link" href={urlAtTime(s.video_url, s.start_sec)} target="_blank" rel="noreferrer">Original source <ArrowUpRightIcon /></a>
            <Report statement={s} reportEmail={reportEmail} />
          </div>
        </div>
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
      <summary><FlagIcon /> Report a problem</summary>
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
