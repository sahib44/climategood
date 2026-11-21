import { useEffect, useRef } from 'react'

// Full-screen landing background: the color loop plays; wherever the pointer has just been,
// the same scene shows as ink on paper, in pixel blocks that fade out ("etch trail").
//
// There is only ONE video. The ink version is computed here from the video's own pixels,
// cell by cell. (A second hidden video was tried first: starting it made browsers stop
// painting the visible one.) The loop is drawn by scripts/render_hero.mjs; the numbers
// below match that script. With reduced motion, only the still poster is shown.

const VIDEO_W = 1350, VIDEO_H = 720
const CELL = 6 // the scene's pixel size, in video px
const GW = VIDEO_W / CELL, GH = VIDEO_H / CELL
const BLOCK = 2 // trail block = 2x2 scene cells
const RADIUS = 4.2 // brush radius, in blocks
const FADE = 0.022 // ink lost per frame (about 0.8 s to clear)
const SUN = { x: 150, y: 81, r: 13.5 } // in cells; the sun prints in the accent color
const PAPER = '#f6f1e4', INK = '#161a22', ACCENT = '#1c48ea'

const VIDEO = '/hero/firsthand-loopA-1350x720.mp4'
const POSTER = '/hero/firsthand-poster.jpg'

// 8x8 ordered-dither threshold in 0..1, the same pattern the renderer uses.
function bayer(x, y) {
  let v = 0
  for (let bit = 0; bit < 3; bit++) {
    const xb = (x >> bit) & 1, yb = (y >> bit) & 1
    v = (v << 2) | ((xb ^ yb) << 1) | yb
  }
  return (v + 0.5) / 64
}

export default function HeroEtch() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    const video = videoRef.current, canvas = canvasRef.current
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    // React does not reliably set the muted attribute, and browsers only autoplay muted video.
    video.muted = true
    const start = () => video.play().catch(() => {})
    start()
    video.addEventListener('canplay', start, { once: true })

    const ctx = canvas.getContext('2d')
    // The current video frame, shrunk to one pixel per scene cell, so it can be read cheaply.
    const small = document.createElement('canvas')
    small.width = GW
    small.height = GH
    const sctx = small.getContext('2d', { willReadFrequently: true })

    const cols = Math.ceil(GW / BLOCK), rows = Math.ceil(GH / BLOCK)
    const ink = new Float32Array(cols * rows)
    let fit = { scale: 1, ox: 0, oy: 0 }
    let last = null, raf = 0, active = false

    function resize() {
      const { width, height } = canvas.getBoundingClientRect()
      canvas.width = Math.round(width)
      canvas.height = Math.round(height)
      // Same math as object-fit: cover, anchored to the bottom like the video.
      const scale = Math.max(width / VIDEO_W, height / VIDEO_H)
      fit = { scale, ox: (width - VIDEO_W * scale) / 2, oy: height - VIDEO_H * scale }
    }

    function stamp(x, y) {
      const size = BLOCK * CELL * fit.scale
      const bx = (x - fit.ox) / size, by = (y - fit.oy) / size
      for (let r = Math.floor(by - RADIUS); r <= by + RADIUS; r++) {
        for (let c = Math.floor(bx - RADIUS); c <= bx + RADIUS; c++) {
          if (r < 0 || c < 0 || r >= rows || c >= cols) continue
          const d = Math.hypot(c + 0.5 - bx, r + 0.5 - by) / RADIUS
          // Ragged edge: blocks near the rim are kept at random, so the trail looks etched.
          if (d < 1 && (d < 0.55 || Math.random() > d)) ink[r * cols + c] = Math.max(ink[r * cols + c], 1 - d * 0.5)
        }
      }
    }

    function onMove(e) {
      const rect = canvas.getBoundingClientRect()
      const x = e.clientX - rect.left, y = e.clientY - rect.top
      // Fill in between events so a fast pointer leaves an unbroken line.
      const step = BLOCK * CELL * fit.scale
      const steps = last ? Math.min(40, Math.ceil(Math.hypot(x - last.x, y - last.y) / step)) : 1
      for (let i = 1; i <= steps; i++) stamp(last ? last.x + ((x - last.x) * i) / steps : x, last ? last.y + ((y - last.y) * i) / steps : y)
      last = { x, y }
      if (!active) {
        active = true
        raf = requestAnimationFrame(draw)
      }
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      let px = null
      if (video.readyState >= 2) {
        sctx.drawImage(video, 0, 0, GW, GH)
        px = sctx.getImageData(0, 0, GW, GH).data
      }
      const size = CELL * fit.scale
      let any = false
      for (let i = 0; i < ink.length; i++) {
        if (ink[i] <= 0) continue
        ink[i] -= FADE
        if (ink[i] <= 0) continue
        any = true
        if (!px) continue
        const bc = i % cols, br = (i - bc) / cols
        for (let dy = 0; dy < BLOCK; dy++) {
          for (let dx = 0; dx < BLOCK; dx++) {
            const cx = bc * BLOCK + dx, cy = br * BLOCK + dy
            if (cx >= GW || cy >= GH) continue
            const k = (cy * GW + cx) * 4
            const lum = (0.2126 * px[k] + 0.7152 * px[k + 1] + 0.0722 * px[k + 2]) / 255
            ctx.fillStyle =
              Math.hypot(cx - SUN.x, cy - SUN.y) < SUN.r && px[k] > 200 && px[k + 2] < 190
                ? ACCENT
                : lum + (bayer(cx, cy) - 0.5) * 0.42 > 0.56 ? PAPER : INK
            // Whole cells, snapped to device pixels: they switch off, never go translucent.
            const x0 = Math.round(fit.ox + cx * size), y0 = Math.round(fit.oy + cy * size)
            ctx.fillRect(x0, y0, Math.round(fit.ox + (cx + 1) * size) - x0, Math.round(fit.oy + (cy + 1) * size) - y0)
          }
        }
      }
      if (any) raf = requestAnimationFrame(draw)
      else active = false
    }

    const onLeave = () => (last = null)
    // The scene is full-screen, so the pointer is tracked across the whole page.
    const host = document.documentElement
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)
    host.addEventListener('pointermove', onMove)
    host.addEventListener('pointerleave', onLeave)
    return () => {
      cancelAnimationFrame(raf)
      observer.disconnect()
      host.removeEventListener('pointermove', onMove)
      host.removeEventListener('pointerleave', onLeave)
    }
  }, [])

  return (
    <div className="hero-etch" aria-hidden="true">
      <img src={POSTER} alt="" />
      <video ref={videoRef} src={VIDEO} poster={POSTER} muted loop playsInline preload="auto" />
      <canvas ref={canvasRef} />
    </div>
  )
}
