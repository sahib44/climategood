import { useState } from 'react'
import { getHealth, getTopicResult, getTopics } from '../api.js'
import { coverageText, formatDate, initials, useAsync } from '../lib.js'
import { CheckIcon, VideoIcon } from '../components/icons.jsx'
import ClipCard from '../components/ClipCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import Label from '../components/Label.jsx'

export default function CandidatePage({ id, data }) {
  const topics = useAsync(getTopics, [])
  const health = useAsync(getHealth, [])
  const [picked, setPicked] = useState(null) // null = default to the first topic in the fixed list

  if (!data) return <main className="page"><p className="notice">Loading…</p></main>
  const entry = data.candidates.find((c) => c.candidate.id === id)
  if (!entry) {
    return <main className="page"><p className="notice">We have no candidate with that id. <a href="#/">Back to search</a></p></main>
  }
  const { candidate: c, coverage } = entry
  const list = topics.data || []
  const selected = picked || new Set(list.slice(0, 1).map((t) => t.id))
  const toggle = (topicId) => {
    const next = new Set(selected)
    next.has(topicId) ? next.delete(topicId) : next.add(topicId)
    setPicked(next)
  }

  return (
    <main className="page">
      <a className="back" href="#/">← Back to search</a>

      <section className="card profile">
        <span className="avatar" aria-hidden="true">{initials(c.name)}</span>
        <div>
          <h1>{c.name}</h1>
          <p className="muted">
            {c.office} · {c.party} · {c.jurisdiction} · Election: {formatDate(c.election_date)}
          </p>
        </div>
        <p className="coverage">
          <VideoIcon />
          <span>
            <strong>Coverage:</strong> {coverageText(coverage)} <Label>{coverage.label}</Label>
            {c.sources.length > 0 && (
              <> · Sources:{' '}
                {c.sources.map((s, i) => (
                  <span key={s}>{i > 0 && ', '}<a href={s} target="_blank" rel="noreferrer">{hostname(s)}</a></span>
                ))}
              </>
            )}
          </span>
          <a className="how" href="#/about">How we verified</a>
        </p>
      </section>

      {data.unevenness_warning && (
        <p className="coverage-warning"><strong>Coverage note:</strong> {data.unevenness_warning}</p>
      )}

      <fieldset className="topics">
        <legend>Topics</legend>
        {topics.error && <p role="alert" className="notice">Could not load topics ({topics.error}).</p>}
        {list.map((t) => (
          <label key={t.id} className={selected.has(t.id) ? 'chip chip-on' : 'chip'} title={t.description}>
            <input type="checkbox" checked={selected.has(t.id)} onChange={() => toggle(t.id)} />
            <span className="box"><CheckIcon /></span>
            {t.label}
          </label>
        ))}
      </fieldset>

      {/* Fixed topic order (config/topics.json), not the order clicked and not by result count. */}
      {list.filter((t) => selected.has(t.id)).map((t) => (
        <TopicSection key={t.id} candidate={c} topic={t} reportEmail={health.data?.report_email} />
      ))}
      {list.length > 0 && selected.size === 0 && <p className="notice">Pick a topic above to see what was said.</p>}
    </main>
  )
}

function TopicSection({ candidate, topic, reportEmail }) {
  const { data, error } = useAsync(() => getTopicResult(candidate.id, topic.id), [candidate.id, topic.id])
  return (
    <section className="topic-section">
      <h2>{topic.label}</h2>
      <p className="muted">{topic.description}</p>
      {error && <p role="alert" className="notice">Could not load this topic ({error}).</p>}
      {!data && !error && <p className="notice">Loading…</p>}
      {data && data.cards.length > 0 && (
        <>
          <p className="count muted">
            {data.cards.length} statement{data.cards.length === 1 ? '' : 's'} found, oldest first. All matches are shown.
          </p>
          <ol className="timeline">
            {/* Rule 5: every match, chronological, never truncated. */}
            {data.cards.map((card) => (
              <ClipCard key={card.statement.id} card={card} reportEmail={reportEmail} />
            ))}
          </ol>
        </>
      )}
      {data && data.cards.length === 0 && (
        <EmptyState result={data} />
      )}
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
