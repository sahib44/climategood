import { getCandidates } from './api.js'
import { useAsync, useRoute } from './lib.js'
import Search from './pages/Search.jsx'
import CandidatePage from './pages/Candidate.jsx'
import About from './pages/About.jsx'
import { Privacy, Terms } from './pages/Legal.jsx'
import Logo, { Wordmark } from './components/Logo.jsx'

// Rule 1: every candidate renders through the SAME components. No per-party colors,
// no scores, no ranking.

export default function App() {
  const path = useRoute()
  const { data, error } = useAsync(getCandidates, [])
  const candidateId = path.startsWith('/c/') ? decodeURIComponent(path.slice(3)) : null
  const home = path === '/'

  return (
    <div className={home ? 'app app-home' : 'app'}>
      <header className="nav">
        <a className="brand" href="#/"><Logo /> <Wordmark /></a>
        <nav aria-label="Main">
          <a href="#/" aria-current={home ? 'page' : undefined}>Search</a>
          <a href="#/about" aria-current={path === '/about' ? 'page' : undefined}>About</a>
        </nav>
      </header>

      {error && (
        <main className="page">
          <p role="alert" className="notice">Could not load candidates ({error}). Is the backend running on :8000?</p>
        </main>
      )}
      {!error && home && <Search data={data} />}
      {!error && candidateId && <CandidatePage key={candidateId} id={candidateId} data={data} />}
      {!error && path === '/about' && <About />}
      {!error && path === '/terms' && <Terms />}
      {!error && path === '/privacy' && <Privacy />}
      {!error && !home && !candidateId && !['/about', '/terms', '/privacy'].includes(path) && (
        <main className="page"><p className="notice">Page not found. <a href="#/">Back to search</a></p></main>
      )}

      <footer className="footer">
        <a href="#/terms" aria-current={path === '/terms' ? 'page' : undefined}>Terms</a>
        <a href="#/privacy" aria-current={path === '/privacy' ? 'page' : undefined}>Privacy Policy</a>
      </footer>
    </div>
  )
}
