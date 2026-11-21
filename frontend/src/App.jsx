import { getCandidates } from './api.js'
import { useAsync, useRoute } from './lib.js'
import Search from './pages/Search.jsx'
import CandidatePage from './pages/Candidate.jsx'
import About from './pages/About.jsx'

// Rule 1: every candidate renders through the SAME components. No per-party colors,
// no scores, no ranking.

export default function App() {
  const path = useRoute()
  const { data, error } = useAsync(getCandidates, [])
  const candidateId = path.startsWith('/c/') ? decodeURIComponent(path.slice(3)) : null
  const home = path === '/'
  const anyFictional = data?.candidates.some((c) => c.candidate.fictional)

  return (
    <div className={home ? 'app app-home' : 'app'}>
      <header className="nav">
        <a className="brand" href="#/">Firsthand</a>
        <nav aria-label="Main">
          <a href="#/" aria-current={home ? 'page' : undefined}>Search</a>
          <a href="#/about" aria-current={path === '/about' ? 'page' : undefined}>About</a>
        </nav>
      </header>

      {anyFictional && (
        <p className="demo-banner" role="note">
          <strong>Demo data.</strong> These candidates, videos and quotes are fictional placeholders, not real people.
        </p>
      )}

      {error && (
        <main className="page">
          <p role="alert" className="notice">Could not load candidates ({error}). Is the backend running on :8000?</p>
        </main>
      )}
      {!error && home && <Search data={data} />}
      {!error && candidateId && <CandidatePage key={candidateId} id={candidateId} data={data} />}
      {!error && path === '/about' && <About />}
      {!error && !home && !candidateId && path !== '/about' && (
        <main className="page"><p className="notice">Page not found. <a href="#/">Back to search</a></p></main>
      )}

      <footer className="footer">
        Public statements only. Sources linked. No accounts, no tracking. Firsthand does not rate or endorse candidates.
      </footer>
    </div>
  )
}
