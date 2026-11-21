import { useEffect, useState } from 'react'

// Tiny hash router: "#/", "#/c/<candidate id>", "#/about". No dependency, no server rewrites.
export function useRoute() {
  const read = () => window.location.hash.replace(/^#/, '') || '/'
  const [path, setPath] = useState(read)
  useEffect(() => {
    const onChange = () => {
      setPath(read())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return path
}

export function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: null })
  useEffect(() => {
    let live = true
    setState({ data: null, error: null })
    fn().then(
      (data) => live && setState({ data, error: null }),
      (e) => live && setState({ data: null, error: e.message }),
    )
    return () => {
      live = false
    }
  }, deps)
  return state
}

// Rule 1: one fixed order for everyone. Alphabetical, never by results.
export const byName = (a, b) => a.candidate.name.localeCompare(b.candidate.name)

export function initials(name) {
  const words = name.replace(/\(.*?\)/g, '').trim().split(/\s+/)
  return (words[0][0] + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase()
}

export function formatDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function formatTime(sec) {
  const s = Math.floor(sec)
  const h = Math.floor(s / 3600)
  const mm = Math.floor((s % 3600) / 60)
  const ss = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(mm).padStart(2, '0')}:${ss}` : `${mm}:${ss}`
}

// Rule 3: the publisher's own embedded player, starting at the moment. Only YouTube is known
// here; anything else gets a link. youtube-nocookie.com is YouTube's privacy-enhanced player.
function youtubeId(url) {
  try {
    const u = new URL(url)
    if (/(^|\.)youtu\.be$/.test(u.hostname)) return u.pathname.slice(1)
    return /(^|\.)youtube\.com$/.test(u.hostname) ? u.searchParams.get('v') : null
  } catch {
    return null
  }
}

export function embedAtTime(url, sec) {
  const id = youtubeId(url)
  return id ? `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?start=${Math.floor(sec)}&autoplay=1&rel=0` : null
}

// The publisher's own preview image, linked from YouTube (not copied).
export function thumbnailFor(url) {
  const id = youtubeId(url)
  return id ? `https://i.ytimg.com/vi/${encodeURIComponent(id)}/mqdefault.jpg` : null
}

// Rule 3: link to the publisher's own player at the start time. Never re-host.
export function urlAtTime(url, sec) {
  const t = Math.floor(sec)
  try {
    const u = new URL(url)
    if (/(^|\.)youtube\.com$|(^|\.)youtu\.be$/.test(u.hostname)) {
      u.searchParams.set('t', `${t}s`)
      return u.toString()
    }
    u.hash = `t=${t}`
    return u.toString()
  } catch {
    return url
  }
}

export function coverageText({ videos_searched: n, hours_searched: h }) {
  return `${n} video${n === 1 ? '' : 's'} searched · ${h} hour${h === 1 ? '' : 's'}`
}
