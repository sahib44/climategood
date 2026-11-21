import { useEffect } from 'react'
import { getCandidates } from './api.js'
import { useAsync, useRoute } from './lib.js'
import Search from './pages/Search.jsx'
import CandidatePage from './pages/Candidate.jsx'
import About from './pages/About.jsx'
import Report from './pages/Report.jsx'
import { Privacy, Terms } from './pages/Legal.jsx'
import Logo, { Wordmark } from './components/Logo.jsx'

// Rule 1: every candidate renders through the SAME components. No per-party colors,
// no scores, no ranking.

export default function App() {
  const path = useRoute()
  const { data, error } = useAsync(getCandidates, [])
  const candidateId = path.startsWith('/c/') ? decodeURIComponent(path.slice(3)) : null
  const home = path === '/'
  // "#/report/<candidate>/<topic>/<statement>": the report page for one statement.
  const report = path.startsWith('/report/') ? path.slice(8).split('/').map(decodeURIComponent) : null

  // The browser tab names the page you are on.
  const candidateName = data?.candidates.find((c) => c.candidate.id === candidateId)?.candidate.name
  const pageName = candidateName || (report && 'Report a problem') || { '/about': 'About', '/terms': 'Terms', '/privacy': 'Privacy Policy' }[path]
  useEffect(() => {
    document.title = pageName ? `${pageName} · Firsthand` : 'Firsthand'
  }, [pageName])

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
      {!error && report && <Report candidateId={report[0]} topicId={report[1]} statementId={report[2]} />}
      {!error && path === '/about' && <About data={data} />}
      {!error && path === '/terms' && <Terms />}
      {!error && path === '/privacy' && <Privacy />}
      {!error && !home && !candidateId && !report && !['/about', '/terms', '/privacy'].includes(path) && (
        <main className="page"><p className="notice">Page not found. <a href="#/">Back to search</a></p></main>
      )}

      <footer className="footer">
        <a href="#/terms" aria-current={path === '/terms' ? 'page' : undefined}>Terms</a>
        <a href="#/privacy" aria-current={path === '/privacy' ? 'page' : undefined}>Privacy Policy</a>
      </footer>
    </div>
  )
}
