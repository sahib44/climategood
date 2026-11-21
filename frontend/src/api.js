// Where data comes from:
// - dev: the FastAPI backend through the Vite proxy (/api).
// - build with VITE_API_BASE set: that backend. The Vercel deploy uses /api, the same FastAPI app
//   served from the same origin (api/index.py, vercel.json).
// - build without it, or VITE_USE_SNAPSHOT=1: the JSON files in
//   public/snapshot/, written from the real API by scripts/snapshot_api.py.
// Privacy (rule 10): searches are filtered in the browser and never sent anywhere.

const env = import.meta.env
const API_BASE = env.VITE_USE_SNAPSHOT ? null : env.VITE_API_BASE || (env.DEV ? '/api' : null)

export const usingSnapshot = !API_BASE
// The hosted API cannot store reports (see api/index.py), so that build offers the email link only.
export const canPostReports = !!API_BASE && !env.VITE_HOSTED

const cache = new Map()

const json = (url) => fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))

function get(route) {
  if (!cache.has(route)) {
    const snapshot = `${env.BASE_URL}snapshot${route}.json`
    // If the hosted API is down, fall back to the snapshot so the site still answers.
    const request = API_BASE ? json(`${API_BASE}${route}`).catch((e) => (env.DEV ? Promise.reject(e) : json(snapshot))) : json(snapshot)
    request.catch(() => cache.delete(route))
    cache.set(route, request)
  }
  return cache.get(route)
}

export const getHealth = () => get('/health')
export const getTopics = () => get('/topics')
export const getCandidates = () => get('/candidates')
export const getTopicResult = (candidateId, topicId) =>
  get(`/candidates/${encodeURIComponent(candidateId)}/topics/${encodeURIComponent(topicId)}`)

export async function postReport(report) {
  if (!API_BASE) throw new Error('No backend in this build')
  const r = await fetch(`${API_BASE}/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
