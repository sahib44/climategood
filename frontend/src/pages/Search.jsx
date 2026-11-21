import { useState } from 'react'
import { byName, coverageText } from '../lib.js'
import { SearchIcon } from '../components/icons.jsx'

export default function Search({ data }) {
  const [query, setQuery] = useState('')
  const all = data ? [...data.candidates].sort(byName) : []
  const q = query.trim().toLowerCase()
  // Filtered in the browser. The query is never sent or stored (rule 10).
  const matches = q
    ? all.filter(({ candidate: c }) => `${c.name} ${c.office} ${c.jurisdiction}`.toLowerCase().includes(q))
    : []

  function onSubmit(e) {
    e.preventDefault()
    if (matches.length) window.location.hash = `#/c/${encodeURIComponent(matches[0].candidate.id)}`
  }

  return (
    <main className="hero">
      <h1>Firsthand</h1>
      <p className="tagline">Their words. Their clips. No spin, no score.</p>

      <form className="search" role="search" onSubmit={onSubmit}>
        <SearchIcon />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search a candidate or elected official"
          aria-label="Search a candidate or elected official"
          autoComplete="off"
        />
        {q && (
          <ul className="search-results">
            {matches.map(({ candidate: c, coverage }) => (
              <li key={c.id}>
                <a href={`#/c/${encodeURIComponent(c.id)}`}>
                  <span className="result-name">{c.name}</span>
                  <span className="result-meta">{c.office} · {coverageText(coverage)}</span>
                </a>
              </li>
            ))}
            {!matches.length && <li className="search-none">No candidate by that name in our list yet.</li>}
          </ul>
        )}
      </form>

      {!data && <p className="hero-note">Loading…</p>}
      {data && (
        <section className="examples" aria-label="All candidates">
          <p className="hero-note">Everyone we have searched so far, A to Z:</p>
          <ul>
            {all.map(({ candidate: c }) => (
              <li key={c.id}>
                <a className="chip" href={`#/c/${encodeURIComponent(c.id)}`}>
                  <SearchIcon /> {c.name}, {c.office}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data?.unevenness_warning && (
        <p className="coverage-warning"><strong>Coverage note:</strong> {data.unevenness_warning}</p>
      )}
    </main>
  )
}
