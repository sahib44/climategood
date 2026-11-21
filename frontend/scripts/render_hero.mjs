// Renders the landing-page hero loops: an original, procedurally drawn pixel scene
// (daybreak over hills, wind turbines).
//
//   loop A  full color. The hero's base video.
//   loop B  the same scene as ink on paper. Only written with --ink: the site does not ship
//           it, because HeroEtch.jsx computes the same look live from loop A for the cursor trail.
//
// Every frame is computed here; no footage or third-party art is used. Needs ffmpeg on PATH.
//   node frontend/scripts/render_hero.mjs [--ink]    -> public/hero/*.mp4 + poster
//   node frontend/scripts/render_hero.mjs --still 0.25 out.png   (one frame of each, for review)

import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const W = 1350, H = 720, CELL = 6
const GW = W / CELL, GH = H / CELL // 225 x 120 cells
const FPS = 30, FRAMES = 243 // 8.1 s, seamless
const TAU = Math.PI * 2
const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'hero')

const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
const ramp = (...cs) => cs.map(hex)
const SKY = ramp('#2450e6', '#3567ea', '#4f86ee', '#74a8f3', '#a4cbf8', '#d3e6fc', '#fdf3d4')
const SUN = ramp('#fffbe6', '#ffe89a', '#ffcb5c', '#ffb347')
const CLOUD = ramp('#ffffff', '#ffffff', '#eef4ff', '#d3e2fa', '#b4cbf3')
const FAR = ramp('#a9c2f3', '#7d9de6', '#5c7fd8', '#4567c4')
const MID = ramp('#f4cf6a', '#8fcf9d', '#4faa82', '#2f8a68', '#1f6b55')
const NEAR = ramp('#eab544', '#3f9471', '#236650', '#17443a', '#0e2622')
const WHITE = hex('#ffffff'), TOWER = hex('#e6edf9')
const PAPER = hex('#f6f1e4'), INK = hex('#161a22'), ACCENT = hex('#1c48ea')

const BAYER = [
  0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26, 12, 44, 4, 36, 14, 46, 6, 38, 60, 28, 52, 20, 62, 30, 54, 22,
  3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25, 15, 47, 7, 39, 13, 45, 5, 37, 63, 31, 55, 23, 61, 29, 53, 21,
].map((v) => (v + 0.5) / 64)
const bayer = (x, y) => BAYER[(y & 7) * 8 + (x & 7)]
const hash = (x, y) => {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453
  return s - Math.floor(s)
}
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v))
const smooth = (a, b, v) => {
  const t = clamp((v - a) / (b - a))
  return t * t * (3 - 2 * t)
}
// Pick a ramp color for a shade in 0..1 (0 = first color), ordered-dithered between neighbors.
const pick = (r, shade, x, y) => r[clamp(Math.floor(clamp(shade) * (r.length - 1) + bayer(x, y)), 0, r.length - 1)]

// ---------- static geometry ----------
const SUN_X = 150, SUN_Y = 81, SUN_R = 13
const ridgeFar = (x) => 77 + 5 * Math.sin(x * 0.045 + 1.2) + 3 * Math.sin(x * 0.11 + 0.4) + 1.5 * Math.sin(x * 0.27)
const ridgeMid = (x) => 90 + 6 * Math.sin(x * 0.03 + 4.0) + 2.5 * Math.sin(x * 0.09 + 2.0) + Math.sin(x * 0.21 + 1.0)
const ridgeNear = (x) => 105 + 5 * Math.sin(x * 0.024 + 0.6) + 2 * Math.sin(x * 0.075 + 3.1) + Math.sin(x * 0.19)

const TURBINES = [[34, 24, 0.0], [58, 19, 0.37], [186, 22, 0.7], [208, 17, 0.15]].map(([x, h, o]) => ({
  x, hubY: Math.round(ridgeMid(x)) - h, baseY: Math.round(ridgeMid(x)), offset: o, len: Math.round(h * 0.45),
}))

// Cumulus clouds: overlapping puffs on a flat base, lit from above. They sway a few cells
// and breathe slightly instead of travelling, so the loop is seamless. Kept to the sides
// and low in the sky, clear of the headline.
const PUFFS = [[-10, 0, 5], [-4, -3.5, 6.5], [3, -5, 7.5], [10, -2, 6], [15, 0, 4], [0, 0, 6.5]]
const CLOUDS = [
  { x: 24, y: 34, s: 1.25, sway: 3, ph: 0.0 },
  { x: 62, y: 58, s: 0.7, sway: 2, ph: 0.4 },
  { x: 199, y: 30, s: 1.4, sway: 3.5, ph: 0.6 },
  { x: 176, y: 55, s: 0.6, sway: 2, ph: 0.15 },
  { x: 216, y: 66, s: 0.85, sway: 2.5, ph: 0.8 },
  { x: 6, y: 68, s: 0.8, sway: 2, ph: 0.55 },
  { x: 104, y: 70, s: 0.5, sway: 1.5, ph: 0.3 },
]
function cloudAt(x, y, p) {
  for (const c of CLOUDS) {
    const cx = c.x + c.sway * Math.sin(TAU * (p + c.ph))
    const breathe = 1 + 0.05 * Math.sin(TAU * (p + c.ph * 1.7))
    if (y > c.y || Math.abs(x - cx) > 22 * c.s || y < c.y - 14 * c.s) continue
    let inside = false
    for (const [dx, dy, r] of PUFFS) {
      if (Math.hypot(x - (cx + dx * c.s), y - (c.y + dy * c.s)) <= r * c.s * breathe) inside = true
    }
    if (!inside) continue
    const h = (c.y - y) / (12 * c.s) // 0 at the flat base, 1 at the top
    return clamp(0.95 - h * 1.25 + (y === c.y ? 0.15 : 0))
  }
  return -1
}

function segDist(px, py, ax, ay, bx, by) {
  const vx = bx - ax, vy = by - ay
  const t = clamp(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy))
  return Math.hypot(px - ax - vx * t, py - ay - vy * t)
}

// ---------- one cell: returns [color, accent] ----------
function cell(x, y, p) {
  for (const t of TURBINES) {
    if (Math.abs(x - t.x) > t.len + 1 || y > t.baseY || y < t.hubY - t.len - 1) continue
    const a0 = (p / 3 + t.offset) * TAU // a third of a turn per loop: seamless with three blades
    for (let b = 0; b < 3; b++) {
      const a = a0 + (b * TAU) / 3
      if (segDist(x, y, t.x, t.hubY, t.x + Math.cos(a) * t.len, t.hubY + Math.sin(a) * t.len) < 0.62) return [WHITE, false]
    }
    if (x === t.x && y >= t.hubY) return [TOWER, false]
  }
  const land = (ridge, r, depth) => {
    const top = ridge(x)
    const slope = ridge(x + 1.5) - ridge(x - 1.5)
    // Slopes that face the sun are brighter. The side fades through zero under the sun,
    // so there is no hard seam in the hills below it.
    const facing = slope * clamp((SUN_X - x) / 45, -1, 1)
    const fold = 0.5 + 0.5 * Math.sin(x * 0.55 + (y - top) * 0.35 + 2 * Math.sin(x * 0.08)) // gullies
    const shade = 0.42 - facing * 0.22 + ((y - top) / depth) * 0.5 + (fold - 0.5) * 0.3 + (hash(x, y) - 0.5) * 0.18
    return [pick(r, shade, x, y), false]
  }
  if (y >= ridgeNear(x)) return land(ridgeNear, NEAR, 16)
  if (y >= ridgeMid(x)) return land(ridgeMid, MID, 18)
  if (y >= ridgeFar(x)) return land(ridgeFar, FAR, 16)

  // Sky, sun and rays.
  const dx = x - SUN_X, dy = y - SUN_Y, d = Math.hypot(dx, dy)
  if (d < SUN_R) return [pick(SUN, d / SUN_R, x, y), true]
  const rays = Math.cos(Math.atan2(dy, dx) * 18) // 18 rays, still
  const glow = Math.exp(-(d - SUN_R) / 34)
  const shade = Math.pow(y / 84, 1.35) * 0.72 + glow * 0.5 + rays * 0.09 * Math.exp(-(d - SUN_R) / 60)

  const c = cloudAt(x, y, p)
  if (c >= 0) return [pick(CLOUD, c, x, y), false]
  return [pick(SKY, shade, x, y), false]
}

const lum = (c) => (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255

function frame(p, variant) {
  const buf = Buffer.alloc(W * H * 3)
  for (let gy = 0; gy < GH; gy++) {
    for (let gx = 0; gx < GW; gx++) {
      let [c, accent] = cell(gx, gy, p)
      if (variant === 'B') c = accent ? ACCENT : lum(c) + (bayer(gx, gy) - 0.5) * 0.42 > 0.56 ? PAPER : INK
      for (let py = 0; py < CELL; py++) {
        const edge = py === CELL - 1
        let i = ((gy * CELL + py) * W + gx * CELL) * 3
        for (let px = 0; px < CELL; px++) {
          const k = edge || px === CELL - 1 ? 0.9 : 1 // faint grid between cells
          buf[i++] = c[0] * k
          buf[i++] = c[1] * k
          buf[i++] = c[2] * k
        }
      }
    }
  }
  return buf
}

function ffmpeg(args) {
  const proc = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', `${W}x${H}`, '-r', String(FPS), '-i', '-', ...args], {
    stdio: ['pipe', 'inherit', 'inherit'],
  })
  const done = new Promise((res, rej) => proc.on('close', (code) => (code === 0 ? res() : rej(new Error(`ffmpeg exited ${code}`)))))
  const write = (buf) => new Promise((res) => (proc.stdin.write(buf) ? res() : proc.stdin.once('drain', res)))
  return { write, end: () => (proc.stdin.end(), done) }
}

async function video(variant, file) {
  const enc = ffmpeg(['-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', file])
  for (let f = 0; f < FRAMES; f++) await enc.write(frame(f / FRAMES, variant))
  await enc.end()
  console.log('wrote', file)
}

async function still(variant, p, file) {
  const enc = ffmpeg(['-frames:v', '1', '-q:v', '3', file])
  await enc.write(frame(p, variant))
  await enc.end()
}

const args = process.argv.slice(2)
if (args[0] === '--still') {
  await still('A', Number(args[1]), args[2].replace(/(\.\w+)$/, '-A$1'))
  await still('B', Number(args[1]), args[2].replace(/(\.\w+)$/, '-B$1'))
} else {
  mkdirSync(OUT, { recursive: true })
  await video('A', join(OUT, 'firsthand-loopA-1350x720.mp4'))
  if (args.includes('--ink')) await video('B', join(OUT, 'firsthand-loopB-1350x720.mp4'))
  await still('A', 0, join(OUT, 'firsthand-poster.jpg'))
  console.log('wrote poster')
}
