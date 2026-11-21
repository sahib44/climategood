import { getTopicResult } from '../api.js'
import { useAsync } from '../lib.js'
import { InfoIcon } from './icons.jsx'

// Climate integrity score. Added at the product owner's request; it departs from rule 1 in
// AGENTS.md (no scores), so the team should agree on it before it ships.
//
// What it measures: how openly, concretely and consistently a candidate has spoken about the
// five topics in the videos we searched. What it does NOT measure: whether their positions are
// good or bad for the climate. Every input is a count taken from verified statements, so the
// same words always give the same number; the weights are a judgment (modeled).
//
// Computed here in the browser from the API's statement cards. Nothing is stored or sent.

const MIN_VIDEOS = 3 // below this there is too little searched to say anything
const COMMITMENT = /\b(will|won't|would|must|require[sd]?|ban|moratorium|pause|permit[s]?|law|bill|veto|sign|vote[d]?|pledge|guardrails?|protections?|\d+)\b/i

// Each metric has its own color, taken from the landing scene (sky, sun, hills, dusk). A color
// says which metric a slice is; it never says good or bad, and it is the same for everyone.
export const METRICS = [
  { id: 'openness', label: 'Openness', color: '#1c48ea', weight: 0.35, help: 'Topics with at least one verified statement, out of all topics.' },
  { id: 'specificity', label: 'Specificity', color: '#f5a623', weight: 0.25, help: 'Share of statements that name a concrete action, rule or number.' },
  { id: 'consistency', label: 'Consistency', color: '#2f8a68', weight: 0.25, help: 'Share of addressed topics where they spoke on more than one occasion.' },
  { id: 'sourcing', label: 'Sources', color: '#8a5aa8', weight: 0.15, help: 'Share of statements from publisher captions rather than automatic captions.' },
]

// A ring drawn with pathLength=100, so a slice's length is simply its percentage.
function Ring({ size, stroke, slices, children }) {
  const r = (size - stroke) / 2
  let start = 0
  return (
    <span className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`} fill="none" strokeWidth={stroke}>
          <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--soft)" />
          {slices.map((s) => {
            const offset = -start
            start += s.value
            return s.value > 0 && (
              <circle key={s.id} cx={size / 2} cy={size / 2} r={r} pathLength="100" stroke={s.color}
                strokeDasharray={`${s.value} 100`} strokeDashoffset={offset} />
            )
          })}
        </g>
      </svg>
      <span className="ring-label">{children}</span>
    </span>
  )
}

export function integrityScore(results, videosSearched) {
  const cards = results.flatMap((r) => r.cards)
  if (videosSearched < MIN_VIDEOS || cards.length === 0) return null
  const addressed = results.filter((r) => r.cards.length > 0)
  const share = (n, d) => (d ? n / d : 0)
  const values = {
    openness: share(addressed.length, results.length),
    specificity: share(cards.filter((c) => COMMITMENT.test(c.statement.quote_text)).length, cards.length),
    consistency: share(addressed.filter((r) => new Set(r.cards.map((c) => c.statement.video_id)).size > 1).length, addressed.length),
    sourcing: share(cards.filter((c) => c.source.transcript_source !== 'platform_auto_captions').length, cards.length),
  }
  const overall = METRICS.reduce((sum, m) => sum + m.weight * values[m.id], 0)
  return { overall: Math.round(overall * 100), values, statements: cards.length }
}

export default function IntegrityScore({ candidate, topics, coverage }) {
  const { data: results } = useAsync(
    () => Promise.all(topics.map((t) => getTopicResult(candidate.id, t.id))),
    [candidate.id, topics.length],
  )
  if (!topics.length) return null
  const score = results ? integrityScore(results, coverage.videos_searched) : null

  return (
    <section className="integrity card" aria-labelledby="integrity-title">
      <header>
        <h2 id="integrity-title">Climate integrity score</h2>
        <details className="integrity-how">
          <summary aria-label="How this is calculated"><InfoIcon /></summary>
          <div>
            <p>
              How openly, concretely and consistently they have spoken on these topics in the videos we searched.
              Not whether their positions are good or bad for the climate. Fewer videos can mean a lower number.
            </p>
            <ul>
              {METRICS.map((m) => (
                <li key={m.id}><i style={{ background: m.color }} /> <strong>{m.label}</strong> {Math.round(m.weight * 100)}%: {m.help}</li>
              ))}
            </ul>
          </div>
        </details>
      </header>

      {/* The big ring is the overall number: each metric fills its weighted share of it. */}
      <Ring size={148} stroke={16} slices={METRICS.map((m) => ({ ...m, value: score ? score.values[m.id] * m.weight * 100 : 0 }))}>
        {score ? <><b>{score.overall}</b><small>of 100</small></> : <small>{results ? 'Not enough data' : '…'}</small>}
      </Ring>

      <ul className="integrity-metrics">
        {METRICS.map((m) => {
          const pct = score ? Math.round(score.values[m.id] * 100) : null
          return (
            <li key={m.id} title={m.help}>
              <Ring size={64} stroke={8} slices={[{ ...m, value: pct || 0 }]}>
                <b>{pct === null ? '–' : pct}</b>
              </Ring>
              <span>{m.label}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
