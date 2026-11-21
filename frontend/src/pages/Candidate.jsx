import { useState } from 'react'
import { getHealth, getTopicResult, getTopics } from '../api.js'
import { coverageText, formatDate, useAsync } from '../lib.js'
import { ArrowUpRightIcon, ChevronIcon, FlagIcon, TopicIcon, VideoIcon } from '../components/icons.jsx'
import Avatar from '../components/Avatar.jsx'
import ClipCard from '../components/ClipCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import Label from '../components/Label.jsx'

// One candidate's record: who they are, how much we searched, then one topic at a time with
// every statement. Coverage stays on the page in one line (rule 6), not in a box of its own.
export default function CandidatePage({ id, data }) {
  const topics = useAsync(getTopics, [])
  const health = useAsync(getHealth, [])
  const [picked, setPicked] = useState(null) // null = the first topic in the fixed list

  if (!data) return <main className="page page-wide"><p className="notice">Loading…</p></main>
  const entry = data.candidates.find((c) => c.candidate.id === id)
  if (!entry) {
    return <main className="page page-wide"><p className="notice">We have no candidate with that id. <a href="#/">Back to search</a></p></main>
  }
  const { candidate: c, coverage } = entry
  const list = topics.data || []
  const current = list.find((t) => t.id === picked) || list[0]

  return (
    <main className="page page-wide">
      <section className="profile">
        <Avatar candidate={c} />
        <div className="profile-text">
          <h1>{c.name}</h1>
          <p className="running"><FlagIcon /> Candidate for {c.office}, {c.jurisdiction}</p>
          <dl className="facts">
            <div><dt>Party</dt><dd>{c.party}</dd></div>
            <div><dt>Election</dt><dd>{formatDate(c.election_date)}</dd></div>
            {c.current_position && <div><dt>Current position</dt><dd>{c.current_position}</dd></div>}
          </dl>
        </div>
      </section>

      {/* Rule 6: what we searched stays on the page, folded into one panel. */}
      <details className="sources">
        <summary>
          <VideoIcon />
          <span className="sources-title">Sources and coverage</span>
          <span className="sources-count">{coverageText(coverage)}</span>
          <ChevronIcon />
        </summary>
        <div className="sources-body">
          <p>
            {coverage.videos_searched === 0
              ? 'We have not searched any of this candidate’s videos yet.'
              : `We searched ${coverage.videos_searched} of this candidate’s public videos (${coverage.hours_searched} hours). Quotes come only from those videos.`}{' '}
            <Label>{coverage.label}</Label> <a href="#/about">How we verified</a>
          </p>
          {data.unevenness_warning && <p>{data.unevenness_warning}</p>}
          {c.sources.length > 0 && (
            <>
              <h3>Where we looked</h3>
              <ul>
                {c.sources.map((s) => (
                  <li key={s}><a className="icon-link" href={s} target="_blank" rel="noreferrer">{sourceName(s)} <ArrowUpRightIcon /></a></li>
                ))}
              </ul>
            </>
          )}
          {c.photo_credit && <p className="muted">Photo: {c.photo_credit}</p>}
        </div>
      </details>

      {topics.error && <p role="alert" className="notice">Could not load topics ({topics.error}).</p>}
      {current && (
        <div className="record">
          <nav className="topic-nav" aria-label="Topics">
            <h2>Select a topic</h2>
            {/* Fixed topic order (config/topics.json), never by result count. */}
            {list.map((t) => (
              <button key={t.id} type="button" className="topic-pick" aria-pressed={t.id === current.id}
                onClick={() => setPicked(t.id)} title={t.description}>
                <TopicIcon id={t.id} size={18} /> {t.label}
              </button>
            ))}
          </nav>
          <TopicSection key={current.id} candidate={c} topic={current} reportEmail={health.data?.report_email} />
        </div>
      )}
    </main>
  )
}

function TopicSection({ candidate, topic, reportEmail }) {
  const { data: result, error } = useAsync(() => getTopicResult(candidate.id, topic.id), [candidate.id, topic.id])
  const failed = !!error
  return (
    <section className="topic-section">
      <h2><TopicIcon id={topic.id} size={24} /> {topic.label}</h2>
      <p className="muted">{topic.description}</p>
      {failed && <p role="alert" className="notice">Could not load this topic.</p>}
      {!result && !failed && <p className="notice">Loading…</p>}
      {result && result.cards.length > 0 && (
        <>
          <p className="count muted">
            {result.cards.length} statement{result.cards.length === 1 ? '' : 's'} found, oldest first. All matches are shown.
          </p>
          <ol className="timeline">
            {/* Rule 5: every match, chronological, never truncated. */}
            {result.cards.map((card) => (
              <ClipCard key={card.statement.id} card={card} reportEmail={reportEmail} />
            ))}
          </ol>
        </>
      )}
      {result && result.cards.length === 0 && <EmptyState result={result} />}
    </section>
  )
}

// A readable name for a source link: the site, and the original site for archived copies.
function sourceName(url) {
  try {
    const archived = url.match(/^https?:\/\/web\.archive\.org\/web\/\d+\/(.+)$/)
    const u = new URL(archived ? archived[1] : url)
    const name = u.hostname.replace(/^www\./, '') + (u.pathname.length > 1 ? u.pathname.replace(/\/$/, '') : '')
    return archived ? `${name} (archived copy)` : name
  } catch {
    return url
  }
}
