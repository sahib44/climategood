// The page shown while a candidate's record is being searched. The pixel hand assembles as
// the work gets done, and the list below is the real work, as it happens: one line per topic,
// ticked off with what came back. Nothing here is staged except a short pause per step so
// each line can be read.

const HAND = [
  '......##........', '...##.##.##.....', '...##.##.##.##..', '...##.##.##.##..', '...##.##.##.##..',
  '...##.##.##.##..', '...###########..', '##.###########..', '##.###########..', '##############..',
  '##############..', '.#############..', '..############..', '...##########...', '....########....', '....########....',
]
// Every pixel of the hand, in a fixed scattered order, so it fills in the same way each time.
const PIXELS = HAND.flatMap((row, y) => [...row].map((c, x) => (c === '#' ? { x, y } : null)).filter(Boolean))
  .map((p) => ({ ...p, key: (p.x * 73 + p.y * 151 + p.x * p.y * 31) % 97 }))
  .sort((a, b) => a.key - b.key)

export default function SearchProgress({ name, coverage, steps }) {
  const done = steps.filter((s) => s.state === 'done').length
  const lit = Math.round(PIXELS.length * (steps.length ? (done + 0.35) / (steps.length + 0.35) : 0.1))
  return (
    <main className="search-progress" role="status" aria-live="polite">
      <svg className="search-hand" viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true">
        {PIXELS.map((p, i) => <rect key={i} x={p.x} y={p.y} width="1" height="1" className={i < lit ? 'on' : ''} />)}
      </svg>
      <h1>{name}</h1>
      <p className="muted">
        {coverage.videos_searched
          ? `Searching ${coverage.videos_searched} videos, ${coverage.hours_searched} hours of transcript`
          : 'No videos to search yet'}
      </p>
      <ol>
        {steps.map((s) => (
          <li key={s.id} className={`step step-${s.state}`}>
            <i aria-hidden="true" />
            <span>{s.label}</span>
            <em>{s.state === 'active' ? 'searching…' : s.result}</em>
          </li>
        ))}
      </ol>
    </main>
  )
}
