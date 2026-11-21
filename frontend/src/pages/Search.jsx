import { useState } from 'react'
import { byName, coverageText } from '../lib.js'
import { SearchIcon } from '../components/icons.jsx'
import HeroEtch from '../components/HeroEtch.jsx'

// The landing page: the name, one line, and the search box. Nothing else.
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
      <HeroEtch />
      <div className="hero-content">
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
            autoFocus
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
              {!matches.length && (
                <li className="search-none">{data ? 'No candidate by that name in our list yet.' : 'Loading…'}</li>
              )}
            </ul>
          )}
        </form>
      </div>
    </main>
  )
}
