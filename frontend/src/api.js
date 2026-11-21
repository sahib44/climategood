// Where data comes from:
// - dev: the FastAPI backend through the Vite proxy (/api).
// - build with VITE_API_BASE set: that backend (must allow this origin in CORS).
// - build without it (the static Vercel deploy), or VITE_USE_SNAPSHOT=1: the JSON files in
//   public/snapshot/, written from the real API by scripts/snapshot_api.py.
// Privacy (rule 10): searches are filtered in the browser and never sent anywhere.

const env = import.meta.env
const API_BASE = env.VITE_USE_SNAPSHOT ? null : env.VITE_API_BASE || (env.DEV ? '/api' : null)

export const usingSnapshot = !API_BASE

const cache = new Map()

function get(route) {
  if (!cache.has(route)) {
    const url = API_BASE ? `${API_BASE}${route}` : `${env.BASE_URL}snapshot${route}.json`
    const request = fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
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
