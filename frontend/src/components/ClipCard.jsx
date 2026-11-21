import { useState } from 'react'
import { embedAtTime, formatDate, formatTime, thumbnailFor, urlAtTime } from '../lib.js'
import { PlayIcon } from './icons.jsx'

const METHOD = {
  exact_normalized: 'The quote matches the transcript exactly (ignoring case and punctuation).',
  near_exact: 'The quote matches the transcript almost exactly. The text shown is the transcript’s.',
}

// The same card for every candidate (rule 1). The quote is the transcript text from the API,
// shown as-is: never trimmed, reworded or summarized here (rule 2).
// Kept plain: the video, the words, who published it and when, and three quiet links.
// How the quote was checked (rule 8's labels) is one click away, under Context.
export default function ClipCard({ card, topic, order = 0 }) {
  const { statement: s, source } = card
  const [playing, setPlaying] = useState(false)
  const [open, setOpen] = useState(false)
  const embed = embedAtTime(s.video_url, s.start_sec)
  const thumb = thumbnailFor(s.video_url)
  const tile = (
    <>
      {thumb && <img src={thumb} alt="" loading="lazy" />}
      <span className="clip-play-button"><PlayIcon /></span>
      <span className="clip-time">{formatTime(s.start_sec)}</span>
    </>
  )
  return (
    <li className="clip" style={{ '--order': Math.min(order, 6) }}>
      <article className="clip-card">
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
          <blockquote>“{s.quote_text}”</blockquote>
          <p className="clip-meta">
            {source.publisher} · <time dateTime={source.published_date}>{formatDate(source.published_date)}</time>
            {topic && <> · {topic.label}</>}
          </p>
          <p className="clip-links">
            <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}>Context</button>
            <a href={urlAtTime(s.video_url, s.start_sec)} target="_blank" rel="noreferrer">Source</a>
            <a href={`#/report/${encodeURIComponent(s.candidate_id)}/${encodeURIComponent(s.topic_id)}/${encodeURIComponent(s.id)}`}>Report</a>
          </p>
          {open && (
            <div className="context">
              <p>
                {s.context_before && <span className="muted">{s.context_before} </span>}
                <mark>{s.quote_text}</mark>
                {s.context_after && <span className="muted"> {s.context_after}</span>}
              </p>
              <p className="muted">
                From “{source.title}”. {METHOD[s.verification_method] || 'Checked against the transcript.'}{' '}
                Quote: {s.label}. Topic match: {s.topic_match_label}.
              </p>
            </div>
          )}
        </div>
      </article>
    </li>
  )
}
