import { useAsync } from '../lib.js'
import { InfoIcon } from './icons.jsx'

// Climate integrity score. Added at the product owner's request; it departs from rule 1 in
// AGENTS.md (no scores), so the team should agree on it before it ships.
//
// It shows how much, and how concretely, a candidate talks about five specific subjects in the
// videos we searched. The numbers are counted from their transcripts by
// scripts/theme_metrics.py (see that file for the formula) and read from /themes.json.
// It does NOT say whether what they said is good or bad for the climate.

// Each subject has its own color, taken from the landing scene. A color says which subject a
// slice is; it never says good or bad, and it is the same for every candidate.
const COLORS = {
  ai_data_centers: '#1c48ea',
  emissions: '#8a5aa8',
  clean_energy: '#2f8a68',
  water: '#1aa3c4',
  energy_bills: '#f5a623',
}

let themesRequest
const getThemes = () =>
  (themesRequest ||= fetch(`${import.meta.env.BASE_URL}themes.json`).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))))

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

export default function IntegrityScore({ candidate }) {
  const { data } = useAsync(getThemes, [])
  if (!data) return null
  const score = data.candidates[candidate.id]
  const themes = data.themes.map((t) => ({ ...t, color: COLORS[t.id] || '#5b6270', ...(score ? score.themes[t.id] : {}) }))

  return (
    <section className="integrity card" aria-labelledby="integrity-title">
      <header>
        <h2 id="integrity-title">Climate integrity score</h2>
        <details className="integrity-how">
          <summary aria-label="How this is calculated"><InfoIcon /></summary>
          <div>
            <p>
              How much, and how concretely, each subject comes up in the videos we searched. It does not say whether
              what they said is good or bad for the climate, and a video also includes other speakers.
            </p>
            <p>
              Each subject: 40% how many of their videos mention it, 30% how often per hour, 30% how often it comes
              with an action, rule or number. The overall number is the average.
            </p>
          </div>
        </details>
      </header>

      {/* The big ring is the overall number: every subject fills up to a fifth of it. */}
      <Ring size={148} stroke={16} slices={themes.map((t) => ({ ...t, value: (t.value || 0) / themes.length }))}>
        {score ? <><b>{score.overall}</b><small>of 100</small></> : <small>Not enough data</small>}
      </Ring>

      <ul className="integrity-metrics">
        {themes.map((t) => (
          <li key={t.id} title={score ? `${t.mentions} mention${t.mentions === 1 ? '' : 's'} in ${t.videos} of ${score.videos} videos` : undefined}>
            <Ring size={64} stroke={8} slices={[{ ...t, value: t.value || 0 }]}>
              <b>{score ? t.value : '–'}</b>
            </Ring>
            <span>{t.label}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
