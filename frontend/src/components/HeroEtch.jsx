import { useEffect, useRef } from 'react'
import { GW, GH, bayer, createScene } from '../scene.js'

// Full-screen landing background, drawn live on one canvas (no video files).
//
// A full day passes every two minutes: the sun rises, crosses the sky and sets, then the moon
// does the same, and the light on the hills, clouds and sky follows them (see scene.js).
// Wherever the pointer has just been, the scene shows as ink on paper, in pixel blocks that
// fade out ("etch trail"). With reduced motion, one still morning frame is drawn.

const PX = 3 // canvas pixels per scene cell; the last row and column are darkened into a faint grid
const W = GW * PX, H = GH * PX
const DAY_SECONDS = 120
const START = 0.09 // the page opens just after sunrise
const BLOCK = 2 // trail block = 2x2 scene cells
const RADIUS = 4.2 // brush radius, in blocks
const FADE_SECONDS = 0.8
const PAPER = [246, 241, 228], INK = [22, 26, 34], ACCENT = [28, 72, 234]

export default function HeroEtch() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    canvas.width = W
    canvas.height = H
    const ctx = canvas.getContext('2d')
    const image = ctx.createImageData(W, H)
    const out = new Uint32Array(image.data.buffer)
    const scene = createScene()
    const pack = (r, g, b) => (255 << 24) | (b << 16) | (g << 8) | r // little-endian RGBA

    const cols = Math.ceil(GW / BLOCK), rows = Math.ceil(GH / BLOCK)
    const ink = new Float32Array(cols * rows)
    const threshold = new Float32Array(GW * GH)
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) threshold[y * GW + x] = 0.56 - (bayer(x, y) - 0.5) * 0.42

    // Which scene cells are on screen. The canvas is stretched with object-fit: cover and
    // anchored to the bottom, so a tall window shows only the middle of the scene.
    let fit = { scale: 1, left: 0, top: 0 }, view = { x0: 0, x1: GW, y0: 0 }
    function measure() {
      const rect = canvas.getBoundingClientRect()
      if (!rect.width || !rect.height) return
      const scale = Math.max(rect.width / W, rect.height / H)
      fit = { scale, left: rect.left + (rect.width - W * scale) / 2, top: rect.top + rect.height - H * scale }
      const cell = scale * PX
      view = { x0: (rect.left - fit.left) / cell, x1: (rect.right - fit.left) / cell, y0: (rect.top - fit.top) / cell }
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(canvas)

    function paint(seconds) {
      scene.render(seconds, START + seconds / DAY_SECONDS, view)
      const { rgb, sun } = scene
      for (let y = 0, i = 0; y < GH; y++) {
        const inkRow = Math.floor(y / BLOCK) * cols
        for (let x = 0; x < GW; x++, i++) {
          let r = rgb[i * 3], g = rgb[i * 3 + 1], b = rgb[i * 3 + 2]
          if (ink[inkRow + Math.floor(x / BLOCK)] > 0) {
            const c = sun[i] ? ACCENT : (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 > threshold[i] ? PAPER : INK
            r = c[0]
            g = c[1]
            b = c[2]
          }
          const full = pack(r, g, b), edge = pack(r * 0.9, g * 0.9, b * 0.9)
          let o = y * PX * W + x * PX
          for (let py = 0; py < PX; py++, o += W) {
            for (let px = 0; px < PX; px++) out[o + px] = py === PX - 1 || px === PX - 1 ? edge : full
          }
        }
      }
      ctx.putImageData(image, 0, 0)
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      paint(0)
      return () => observer.disconnect()
    }

    const toBlock = (clientX, clientY) => ({
      x: (clientX - fit.left) / fit.scale / PX / BLOCK,
      y: (clientY - fit.top) / fit.scale / PX / BLOCK,
    })

    function stamp(bx, by) {
      for (let r = Math.floor(by - RADIUS); r <= by + RADIUS; r++) {
        for (let c = Math.floor(bx - RADIUS); c <= bx + RADIUS; c++) {
          if (r < 0 || c < 0 || r >= rows || c >= cols) continue
          const d = Math.hypot(c + 0.5 - bx, r + 0.5 - by) / RADIUS
          // Ragged edge: blocks near the rim are kept at random, so the trail looks etched.
          if (d < 1 && (d < 0.55 || Math.random() > d)) ink[r * cols + c] = Math.max(ink[r * cols + c], 1 - d * 0.5)
        }
      }
    }

    let last = null, trailing = false
    function onMove(e) {
      const at = toBlock(e.clientX, e.clientY)
      // Fill in between events so a fast pointer leaves an unbroken line.
      const steps = last ? Math.min(40, Math.ceil(Math.hypot(at.x - last.x, at.y - last.y))) : 1
      for (let i = 1; i <= steps; i++) stamp(last ? last.x + ((at.x - last.x) * i) / steps : at.x, last ? last.y + ((at.y - last.y) * i) / steps : at.y)
      last = at
      trailing = true
    }
    const onLeave = () => (last = null)

    // 30 frames a second while a trail is fading, 12 otherwise: the scene itself moves slowly.
    const began = performance.now()
    let raf = 0, drawn = 0
    function frame(now) {
      raf = requestAnimationFrame(frame)
      const gap = now - drawn
      if (gap < (trailing ? 33 : 83)) return
      drawn = now
      if (trailing) {
        const lost = Math.min(gap, 100) / 1000 / FADE_SECONDS
        trailing = false
        for (let i = 0; i < ink.length; i++) {
          if (ink[i] <= 0) continue
          ink[i] -= lost
          if (ink[i] > 0) trailing = true
        }
      }
      paint((now - began) / 1000)
    }
    raf = requestAnimationFrame(frame)

    // The scene is full-screen, so the pointer is tracked across the whole page.
    const host = document.documentElement
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
      <canvas ref={canvasRef} />
    </div>
  )
}
