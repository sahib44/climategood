// The landing scene, computed cell by cell: hills, wind turbines, clouds, and a sun and moon
// that rise and set. Original and procedural: no footage or third-party art.
//
// No DOM in this file, so it can also run in Node. HeroEtch.jsx draws it on a canvas.
//
//   const scene = createScene()
//   scene.render(seconds, tod, view)   // tod = time of day, 0..1 (0 sunrise, 0.25 noon, 0.5 sunset, 0.75 midnight)
//                                      // view = the cells on screen, { x0, x1, y0 }; optional
//   scene.rgb                    // Uint8Array, GW*GH*3
//   scene.sun                    // Uint8Array, 1 where the cell is part of the sun

export const GW = 225, GH = 120 // the scene's size in cells
const N = GW * GH
const TAU = Math.PI * 2
const LOOP = 8.1 // seconds for one cloud sway and a third of a turbine turn

const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
const ramp = (...cs) => cs.map(hex)
const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v)
const smooth = (a, b, v) => {
  const t = clamp((v - a) / (b - a))
  return t * t * (3 - 2 * t)
}
const hash = (x, y) => {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453
  return s - Math.floor(s)
}
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]

// 8x8 ordered dither, 0..1.
export function bayer(x, y) {
  let v = 0
  for (let bit = 0; bit < 3; bit++) {
    const xb = (x >> bit) & 1, yb = (y >> bit) & 1
    v = (v << 2) | ((xb ^ yb) << 1) | yb
  }
  return (v + 0.5) / 64
}

// ---------- palettes: each ramp runs light to dark (sky: zenith to horizon) ----------
const DAY = {
  sky: ramp('#2450e6', '#3567ea', '#4f86ee', '#74a8f3', '#a4cbf8', '#d3e6fc', '#fdf3d4'),
  cloud: ramp('#ffffff', '#ffffff', '#eef4ff', '#d3e2fa', '#b4cbf3'),
  far: ramp('#a9c2f3', '#7d9de6', '#5c7fd8', '#4567c4'),
  mid: ramp('#f4cf6a', '#8fcf9d', '#4faa82', '#2f8a68', '#1f6b55'),
  near: ramp('#eab544', '#3f9471', '#236650', '#17443a', '#0e2622'),
  blade: hex('#ffffff'), tower: hex('#e6edf9'),
}
const NIGHT = {
  sky: ramp('#070b24', '#0a1130', '#0f1a42', '#152555', '#1c3168', '#253f7c', '#31508f'),
  cloud: ramp('#6577b0', '#56689f', '#45558a', '#364474', '#29355f'),
  far: ramp('#2a3a78', '#223066', '#1b2754', '#151f45'),
  mid: ramp('#2f6170', '#215260', '#18414e', '#11323d', '#0c252e'),
  near: ramp('#1c4651', '#12353e', '#0c282f', '#081c22', '#051317'),
  blade: hex('#c9d4f0'), tower: hex('#9fb0d8'),
}
// Sunrise and sunset: what the sky and the light turn toward while the sun is near the horizon.
const DUSK_SKY = ramp('#1d2470', '#3a2f8a', '#6a3f9c', '#a8518f', '#e0707a', '#f7a35c', '#ffd889')
const DUSK_CLOUD = hex('#ff9f8a'), DUSK_FAR = hex('#8a5aa8'), DUSK_LAND = hex('#e8925a')
const SUN_HIGH = ramp('#fffbe6', '#ffe89a', '#ffcb5c', '#ffb347')
const SUN_LOW = ramp('#fff0c0', '#ffc070', '#ff9a4a', '#ff6f3c')
const MOON = ramp('#fffdf0', '#f6f2dc', '#dfe0d2')
const STAR = [hex('#fdf6d8'), hex('#9fb4e8')]
const SUN_R = 11, MOON_R = 7.5

// ---------- fixed geometry ----------
const ridgeFar = (x) => 77 + 5 * Math.sin(x * 0.045 + 1.2) + 3 * Math.sin(x * 0.11 + 0.4) + 1.5 * Math.sin(x * 0.27)
const ridgeMid = (x) => 90 + 6 * Math.sin(x * 0.03 + 4.0) + 2.5 * Math.sin(x * 0.09 + 2.0) + Math.sin(x * 0.21 + 1.0)
const ridgeNear = (x) => 105 + 5 * Math.sin(x * 0.024 + 0.6) + 2 * Math.sin(x * 0.075 + 3.1) + Math.sin(x * 0.19)
const TURBINES = [[34, 24, 0.0], [58, 19, 0.37], [186, 22, 0.7], [208, 17, 0.15]].map(([x, h, o]) => ({
  x, hubY: Math.round(ridgeMid(x)) - h, baseY: Math.round(ridgeMid(x)), offset: o, len: Math.round(h * 0.45),
}))
// Cumulus clouds: overlapping puffs on a flat base. They sway and breathe in place.
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

// Where the sun is at a time of day; the moon is half a day behind it. The arc is fitted to
// the part of the scene that is on screen (view), so both rise and set in sight on any screen shape.
const FULL_VIEW = { x0: 0, x1: GW, y0: 0 }
function orbit(tod, view) {
  const a = TAU * tod
  const mid = (view.x0 + view.x1) / 2, reach = ((view.x1 - view.x0) / 2) * 0.86
  return { x: mid - reach * Math.cos(a), y: 92 - (76 - view.y0) * Math.sin(a), up: Math.sin(a) }
}

export function createScene() {
  // Worked out once: which layer each cell is in, and the parts of its shading that never change.
  const kind = new Uint8Array(N) // 0 sky, 1 far hills, 2 mid, 3 near
  const base = new Float32Array(N) // land: shade before lighting. sky: star brightness (0 = none)
  const slope = new Float32Array(N) // land: how much the cell tilts left or right
  const dith = new Float32Array(N)
  for (let y = 0; y < GH; y++) {
    for (let x = 0; x < GW; x++) {
      const i = y * GW + x
      dith[i] = bayer(x, y)
      const layer = y >= ridgeNear(x) ? [3, ridgeNear, 16] : y >= ridgeMid(x) ? [2, ridgeMid, 18] : y >= ridgeFar(x) ? [1, ridgeFar, 16] : null
      if (!layer) {
        const s = hash(x * 3.1 + 7, y * 7.7 + 3)
        base[i] = y < 72 && s > 0.9925 ? s : 0
        continue
      }
      const [k, ridge, depth] = layer
      const top = ridge(x)
      const fold = 0.5 + 0.5 * Math.sin(x * 0.55 + (y - top) * 0.35 + 2 * Math.sin(x * 0.08)) // gullies
      kind[i] = k
      slope[i] = ridge(x + 1.5) - ridge(x - 1.5)
      base[i] = 0.42 + ((y - top) / depth) * 0.5 + (fold - 0.5) * 0.3 + (hash(x, y) - 0.5) * 0.18
    }
  }

  const rgb = new Uint8Array(N * 3)
  const sunMask = new Uint8Array(N)
  const side = new Float32Array(GW)
  const put = (i, c) => {
    rgb[i * 3] = c[0]
    rgb[i * 3 + 1] = c[1]
    rgb[i * 3 + 2] = c[2]
  }
  const pick = (r, shade, i) => r[clamp(Math.floor(clamp(shade) * (r.length - 1) + dith[i]), 0, r.length - 1)]

  function render(sec, tod, view = FULL_VIEW) {
    const sun = orbit(tod, view), moon = orbit(tod + 0.5, view)
    const day = smooth(-0.12, 0.3, sun.up) // 0 night .. 1 full day
    const gold = Math.exp(-((sun.up / 0.25) ** 2)) // 1 while the sun is at the horizon
    const sunUp = smooth(-0.1, 0.15, sun.up), moonUp = smooth(-0.1, 0.15, moon.up)
    const low = 1 - smooth(0, 0.5, sun.up)

    // This moment's colors: night to day, pulled toward sunset colors near the horizon.
    const blend = (key, tint, amount) => DAY[key].map((c, k) => mix(mix(NIGHT[key][k], c, day), tint, amount))
    const sky = DAY.sky.map((c, k) => mix(mix(NIGHT.sky[k], c, day), DUSK_SKY[k], gold * 0.85))
    const cloud = blend('cloud', DUSK_CLOUD, gold * 0.45)
    const land = [null, blend('far', DUSK_FAR, gold * 0.35), blend('mid', DUSK_LAND, gold * 0.2), blend('near', DUSK_LAND, gold * 0.14)]
    const sunRamp = SUN_HIGH.map((c, k) => mix(c, SUN_LOW[k], low))
    const blade = mix(mix(NIGHT.blade, DAY.blade, day), DUSK_CLOUD, gold * 0.3)
    const tower = mix(mix(NIGHT.tower, DAY.tower, day), DUSK_CLOUD, gold * 0.3)

    // Slopes facing the light are brighter. The light is the sun by day and the moon, weaker, by night;
    // as it crosses the sky the lit side of every hill moves with it.
    const sunLight = smooth(-0.05, 0.3, sun.up), moonLight = 0.5 * smooth(0, 0.3, moon.up)
    for (let x = 0; x < GW; x++) side[x] = clamp((sun.x - x) / 45, -1, 1) * sunLight + clamp((moon.x - x) / 45, -1, 1) * moonLight
    const dim = (1 - sunLight) * (1 - moonLight) * 0.12 // with no light in the sky, the land sinks into shadow

    sunMask.fill(0)
    for (let y = 0, i = 0; y < GH; y++) {
      for (let x = 0; x < GW; x++, i++) {
        const k = kind[i]
        if (k) {
          put(i, pick(land[k], base[i] - slope[i] * side[x] * 0.22 + dim, i))
          continue
        }
        const ds = Math.hypot(x - sun.x, y - sun.y)
        if (ds < SUN_R) {
          put(i, pick(sunRamp, ds / SUN_R, i))
          sunMask[i] = 1
          continue
        }
        const dm = Math.hypot(x - moon.x, y - moon.y)
        if (dm < MOON_R && Math.hypot(x - (moon.x + 3.6), y - (moon.y - 2.2)) > MOON_R * 0.86) {
          put(i, pick(MOON, dm / MOON_R, i))
          continue
        }
        // Stars come out one by one as the light goes.
        if (base[i] && 1 - day > 0.25 + ((base[i] - 0.9925) / 0.0075) * 0.6) {
          put(i, STAR[base[i] > 0.9965 ? 0 : 1])
          continue
        }
        let shade = Math.pow(y / 84, 1.35 + 0.25 * (1 - day)) * (0.72 + 0.08 * (1 - day))
        shade += Math.exp(-(ds - SUN_R) / 34) * 0.5 * sunUp + Math.exp(-dm / 16) * 0.3 * moonUp
        if (sunUp > 0 && ds < 90) shade += Math.cos(Math.atan2(y - sun.y, x - sun.x) * 18) * 0.09 * Math.exp(-(ds - SUN_R) / 60) * sunUp
        put(i, pick(sky, shade, i))
      }
    }

    // Clouds, in front of the sky, sun, moon and stars.
    const p = sec / LOOP
    for (const c of CLOUDS) {
      const cx = c.x + c.sway * Math.sin(TAU * (p + c.ph))
      const breathe = 1 + 0.05 * Math.sin(TAU * (p + c.ph * 1.7))
      const x0 = Math.max(0, Math.floor(cx - 22 * c.s)), x1 = Math.min(GW - 1, Math.ceil(cx + 22 * c.s))
      for (let y = Math.max(0, Math.floor(c.y - 14 * c.s)); y <= c.y; y++) {
        for (let x = x0; x <= x1; x++) {
          const i = y * GW + x
          if (kind[i]) continue
          let inside = false
          for (const [dx, dy, r] of PUFFS) {
            if (Math.hypot(x - (cx + dx * c.s), y - (c.y + dy * c.s)) <= r * c.s * breathe) inside = true
          }
          if (!inside) continue
          const h = (c.y - y) / (12 * c.s) // 0 at the flat base, 1 at the top
          put(i, pick(cloud, 0.95 - h * 1.25 + (y === c.y ? 0.15 : 0), i))
          sunMask[i] = 0
        }
      }
    }

    // Turbines, in front of everything.
    for (const t of TURBINES) {
      const a0 = (p / 3 + t.offset) * TAU
      for (let y = t.hubY - t.len - 1; y <= t.baseY; y++) {
        for (let x = t.x - t.len - 1; x <= t.x + t.len + 1; x++) {
          if (x < 0 || x >= GW || y < 0 || y >= GH) continue
          let hit = null
          for (let b = 0; b < 3 && !hit; b++) {
            const a = a0 + (b * TAU) / 3
            const vx = Math.cos(a) * t.len, vy = Math.sin(a) * t.len
            const u = clamp(((x - t.x) * vx + (y - t.hubY) * vy) / (vx * vx + vy * vy))
            if (Math.hypot(x - t.x - vx * u, y - t.hubY - vy * u) < 0.62) hit = blade
          }
          if (!hit && x === t.x && y >= t.hubY) hit = tower
          if (hit) {
            put(y * GW + x, hit)
            sunMask[y * GW + x] = 0
          }
        }
      }
    }
  }

  return { render, rgb, sun: sunMask }
}
