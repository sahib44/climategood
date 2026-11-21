import { useEffect, useState } from 'react'

// STUB: lists candidates + coverage. Next (Owner B): topic checklist, ClipCard, EmptyState,
// report-a-problem. Rule: every candidate renders through the SAME components. No colors per party,
// no scores, no ranking. Order candidates alphabetically, never by results.

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/candidates')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <main>
      <h1>OnRecord</h1>
      <p className="tagline">What candidates actually said, word for word. No scores. No rankings.</p>

      {error && <p role="alert">Could not reach the API ({error}). Is the backend running on :8000?</p>}
      {!data && !error && <p>Loading…</p>}

      {data?.unevenness_warning && (
        <p className="warning"><strong>Coverage note:</strong> {data.unevenness_warning}</p>
      )}

      {data && (
        <ul className="candidates">
          {[...data.candidates]
            .sort((a, b) => a.candidate.name.localeCompare(b.candidate.name))
            .map(({ candidate, coverage }) => (
              <li key={candidate.id}>
                <span className="name">{candidate.name}</span>
                <span className="meta">{candidate.office} · {candidate.party}</span>
                <span className="meta">
                  Searched {coverage.videos_searched} video{coverage.videos_searched === 1 ? '' : 's'},{' '}
                  {coverage.hours_searched} h <em>({coverage.label})</em>
                </span>
              </li>
            ))}
        </ul>
      )}

      <footer>OnRecord does not rate or endorse candidates. No accounts, no tracking.</footer>
    </main>
  )
}
