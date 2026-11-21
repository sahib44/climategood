import { useEffect, useRef } from 'react'
import { initials } from '../lib.js'

const CELLS = 14 // the photo is redrawn at 14x14 and scaled up, like the home page's pixels

// A candidate's picture: their photo if the data has one (photo_url, with photo_credit),
// otherwise their initials. The same square frame for everyone (rule 1). Hovering a photo
// shows it in pixels, the site's motif.
export default function Avatar({ candidate, size }) {
  const canvasRef = useRef(null)
  const imgRef = useRef(null)

  // Draw the top-centre square of the photo, small. Drawing a photo from another site is
  // allowed; only reading the pixels back is not, and we never do.
  const pixelate = () => {
    const img = imgRef.current, canvas = canvasRef.current
    const side = img ? Math.min(img.naturalWidth, img.naturalHeight) : 0
    if (!canvas || !side) return
    canvas.width = canvas.height = CELLS
    canvas.getContext('2d').drawImage(img, (img.naturalWidth - side) / 2, 0, side, side, 0, 0, CELLS, CELLS)
  }
  // A photo already in the browser's cache can finish loading before onLoad is attached.
  useEffect(() => {
    if (imgRef.current?.complete) pixelate()
  }, [candidate.photo_url])

  const style = size ? { width: size, height: size, fontSize: size * 0.38 } : undefined
  if (!candidate.photo_url) {
    return <span className="avatar" style={style} aria-hidden="true">{initials(candidate.name)}</span>
  }
  return (
    <span className="avatar avatar-photo" style={style} title={candidate.photo_credit || undefined}>
      <img ref={imgRef} src={candidate.photo_url} alt="" onLoad={pixelate} />
      <canvas ref={canvasRef} aria-hidden="true" />
    </span>
  )
}
