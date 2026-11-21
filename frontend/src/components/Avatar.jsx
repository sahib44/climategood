import { initials } from '../lib.js'

// A candidate's picture: their photo if the data has one (photo_url, with photo_credit),
// otherwise their initials. The same square frame for everyone (rule 1).
export default function Avatar({ candidate, size }) {
  const style = size ? { width: size, height: size, fontSize: size * 0.38 } : undefined
  return candidate.photo_url ? (
    <img className="avatar" style={style} src={candidate.photo_url} alt="" title={candidate.photo_credit || undefined} loading="lazy" />
  ) : (
    <span className="avatar" style={style} aria-hidden="true">{initials(candidate.name)}</span>
  )
}
