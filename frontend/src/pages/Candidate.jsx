import { useState } from 'react'
import { getHealth, getTopicResult, getTopics } from '../api.js'
import { coverageText, formatDate, useAsync } from '../lib.js'
import { ArrowLeftIcon, BriefcaseIcon, CalendarIcon, FlagIcon, TopicIcon, VideoIcon } from '../components/icons.jsx'
import Avatar from '../components/Avatar.jsx'
import ClipCard from '../components/ClipCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import Label from '../components/Label.jsx'

// One candidate's record. Layout: who they are and what we searched; a snapshot of how many
// statements we found on each topic; then one topic at a time with every statement.
// The snapshot counts statements. It never says whether a statement supports or opposes
// anything, and it uses one color for every topic (rules 1 and 7).
export default function CandidatePage({ id, data }) {
  const topics = useAsync(getTopics, [])
  const health = useAsync(getHealth, [])
  const list = topics.data || []
  // Every topic's result is loaded up front, so the snapshot can show the counts.
  const results = useAsync(
    () => Promise.all(list.map((t) => getTopicResult(id, t.id).catch(() => null))),
    [id, list.length],
  )
  const [picked, setPicked] = useState(null) // null = the first topic in the fixed list

  if (!data) return <main className="page"><p className="notice">Loading…</p></main>
  const entry = data.candidates.find((c) => c.candidate.id === id)
  if (!entry) {
    return <main className="page"><p className="notice">We have no candidate with that id. <a href="#/">Back to search</a></p></main>
  }
  const { candidate: c, coverage } = entry
  const current = list.find((t) => t.id === picked) || list[0]
  const resultFor = (topic) => results.data?.[list.indexOf(topic)] || null
  const counts = list.map((t) => resultFor(t)?.cards.length ?? null)
  const loaded = list.length > 0 && counts.every((n) => n !== null)
  const total = counts.reduce((sum, n) => sum + (n || 0), 0)
  const withStatements = counts.filter((n) => n > 0).length
  const pick = (topicId) => {
    setPicked(topicId)
    document.getElementById('statements')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <main className="page page-wide">
      <a className="back" href="#/"><ArrowLeftIcon /> Back to search</a>

      <section className="profile">
        <Avatar candidate={c} />
        <div className="profile-text">
          <h1>{c.name}</h1>
          <ul className="facts">
            <li><FlagIcon /> Candidate for {c.office}</li>
            {c.current_position && <li><BriefcaseIcon /> {c.current_position}</li>}
            <li>{c.jurisdiction} · {c.party}</li>
            <li><CalendarIcon /> Election: {formatDate(c.election_date)}</li>
          </ul>
          {c.photo_credit && <p className="photo-credit">Photo: {c.photo_credit}</p>}
        </div>
        <aside className="card coverage-card">
          <h2><VideoIcon /> Coverage</h2>
          <p className="coverage-number">{coverageText(coverage)} <Label>{coverage.label}</Label></p>
          {c.sources.length > 0 && (
            <p className="muted">
              Sources:{' '}
              {c.sources.map((s, i) => (
                <span key={s}>{i > 0 && ', '}<a href={s} target="_blank" rel="noreferrer">{hostname(s)}</a></span>
              ))}
            </p>
          )}
          <a className="how" href="#/about">How we verified</a>
        </aside>
      </section>

      {data.unevenness_warning && (
        <p className="coverage-warning"><strong>Coverage note:</strong> {data.unevenness_warning}</p>
      )}

      <section className="snapshot">
        <h2>On the record</h2>
        {topics.error && <p role="alert" className="notice">Could not load topics ({topics.error}).</p>}
        {coverage.videos_searched === 0 && (
          <p className="snapshot-summary">We have not searched any videos for this candidate yet.</p>
        )}
        {loaded && coverage.videos_searched > 0 && (
          <p className="snapshot-summary">
            From the public videos we searched, we found {total} verified statement{total === 1 ? '' : 's'} on{' '}
            {withStatements} of {list.length} topics. <Label>measured</Label>
          </p>
        )}
        <p className="muted">
          This counts what was said, not which side it takes. No statement found does not mean no position.
        </p>
        <div className="snapshot-grid">
          {list.map((t, i) => (
            <button key={t.id} type="button" className="snapshot-card" onClick={() => pick(t.id)}>
              <TopicIcon id={t.id} size={24} />
              <span className="snapshot-label">{t.label}</span>
              <span className={counts[i] ? 'tally tally-some' : 'tally'}>
                {counts[i] === null ? '…' : coverage.videos_searched === 0 ? 'Not searched yet' : counts[i] === 0 ? 'No statement found' : `${counts[i]} statement${counts[i] === 1 ? '' : 's'}`}
              </span>
            </button>
          ))}
        </div>
      </section>

      {current && (
        <div className="record" id="statements">
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
          <TopicSection topic={current} result={resultFor(current)} failed={!!results.data && !resultFor(current)}
            reportEmail={health.data?.report_email} />
        </div>
      )}
    </main>
  )
}

function TopicSection({ topic, result, failed, reportEmail }) {
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

function hostname(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}
