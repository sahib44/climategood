import { useEffect, useState } from 'react'
import { getTopicResult, getTopics } from '../api.js'
import { formatDate, useAsync } from '../lib.js'
import { ArrowUpRightIcon, ChevronIcon, FlagIcon, TopicIcon, VideoIcon } from '../components/icons.jsx'
import Avatar from '../components/Avatar.jsx'
import ClipCard from '../components/ClipCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import IntegrityScore from '../components/IntegrityScore.jsx'

// One candidate's record: who they are, how much we searched, then one topic at a time with
// every statement. Coverage stays on the page in one line (rule 6), not in a box of its own.
export default function CandidatePage({ id, data }) {
  const topics = useAsync(getTopics, [])
  const [picked, setPicked] = useState(null) // null = every topic; otherwise a Set of topic ids

  // The page loads for real: the header shows as soon as we know who this is, and grey
  // placeholders stand where the score and statements will be until every topic's statements
  // have arrived. Then the finished blocks cascade in. No artificial wait beyond a blink
  // (so a fast connection does not flash the placeholders).
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let live = true
    const blink = new Promise((resolve) => setTimeout(resolve, 250))
    const everything = getTopics()
      .then((all) => Promise.all(all.map((t) => getTopicResult(id, t.id).catch(() => null))))
      .catch(() => null)
    Promise.all([everything, blink]).then(() => live && setReady(true))
    return () => {
      live = false
    }
  }, [id])

  if (!data) return <main className="page page-wide" aria-busy="true"><Skeleton header /></main>
  const entry = data.candidates.find((c) => c.candidate.id === id)
  if (!entry) {
    return <main className="page page-wide"><p className="notice">We have no candidate with that id. <a href="#/">Back to search</a></p></main>
  }
  const { candidate: c, coverage } = entry
  const list = topics.data || []
  const selected = picked || new Set(list.map((t) => t.id))
  const toggle = (topicId) => {
    const next = new Set(selected)
    next.has(topicId) ? next.delete(topicId) : next.add(topicId)
    setPicked(next)
  }

  return (
    <main className="page page-wide cascade" aria-busy={!ready}>
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

      {!ready && <Skeleton />}
      {ready && (
        <>
        {/* Rule 6: what we searched stays on the page, folded into one panel. The uneven-coverage
            note is on the About page (About.jsx), at the page owner's request. */}
        <details className="sources">
          <summary>
            <VideoIcon />
            <span className="sources-title">Sources and coverage</span>
            <ChevronIcon />
          </summary>
          <dl className="sources-body">
            <div><dt>Videos searched</dt><dd>{coverage.videos_searched}</dd></div>
            <div><dt>Hours searched</dt><dd>{coverage.hours_searched}</dd></div>
            {c.sources.length > 0 && (
              <div>
                <dt>Sources</dt>
                <dd>
                  {c.sources.map((s) => (
                    <a key={s} className="icon-link" href={s} target="_blank" rel="noreferrer">{sourceName(s)} <ArrowUpRightIcon /></a>
                  ))}
                </dd>
              </div>
            )}
            {c.photo_credit && <div><dt>Photo</dt><dd>{c.photo_credit}</dd></div>}
            <div><dt>Method</dt><dd><a href="#/about">How we verified</a></dd></div>
          </dl>
        </details>

        {topics.error && <p role="alert" className="notice">Could not load topics ({topics.error}).</p>}
        <IntegrityScore candidate={c} topics={list} coverage={coverage} />

        {list.length > 0 && (
          <div className="record">
            <nav className="topic-nav" aria-label="Topics">
              <h2>Select topics</h2>
              {/* Fixed topic order (config/topics.json), never by result count. Any number can be on. */}
              {list.map((t) => (
                <button key={t.id} type="button" className="topic-pick" aria-pressed={selected.has(t.id)}
                  onClick={() => toggle(t.id)} title={t.description}>
                  <TopicIcon id={t.id} size={18} /> {t.label}
                </button>
              ))}
            </nav>
            <div className="statements">
              {coverage.videos_searched === 0 && (
                <p className="notice">We have not searched any videos for this candidate yet.</p>
              )}
              {coverage.videos_searched > 0 && selected.size === 0 && <p className="notice">Pick a topic to see what was said.</p>}
              {coverage.videos_searched > 0 && list.filter((t) => selected.has(t.id)).map((t) => (
                <TopicSection key={t.id} candidate={c} topic={t} />
              ))}
            </div>
          </div>
        )}
        </>
      )}
    </main>
  )
}

// Grey placeholders in the shape of the page, shown while it loads.
function Skeleton({ header }) {
  return (
    <div className="skeleton" aria-hidden="true">
      {header && (
        <div className="profile">
          <span className="avatar bone" />
          <div><span className="bone bone-title" /><span className="bone bone-line" /><span className="bone bone-line bone-short" /></div>
        </div>
      )}
      <span className="bone bone-bar" />
      <span className="bone bone-panel" />
      <div className="record">
        <div className="topic-nav">{[0, 1, 2, 3, 4].map((i) => <span key={i} className="bone bone-pill" />)}</div>
        <div className="statements">
          {[0, 1, 2].map((i) => (
            <div key={i} className="clip-card">
              <span className="bone bone-thumb" />
              <div><span className="bone bone-line" /><span className="bone bone-line" /><span className="bone bone-line bone-short" /></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// One topic's statements: every match, oldest first (rule 5). The topic's name is on each card.
function TopicSection({ candidate, topic }) {
  const { data: result, error } = useAsync(() => getTopicResult(candidate.id, topic.id), [candidate.id, topic.id])
  if (error) return <p role="alert" className="notice">Could not load {topic.label}.</p>
  if (!result) return <p className="notice">Loading…</p>
  if (result.cards.length === 0) return <EmptyState result={result} topic={topic} />
  return (
    <ol className="timeline">
      {result.cards.map((card, i) => (
        <ClipCard key={card.statement.id} card={card} topic={topic} order={i} />
      ))}
    </ol>
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
