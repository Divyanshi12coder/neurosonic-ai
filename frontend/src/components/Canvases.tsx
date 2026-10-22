import { useEffect, useRef } from 'react'
import { mulberry, useActive, usePrefersReducedMotion } from '../lib/util'

function useCanvas(draw: (c: CanvasRenderingContext2D, w: number, h: number, t: number, dt: number) => void, active: boolean, still: boolean, ref: React.RefObject<HTMLCanvasElement>, deps: unknown[] = []) {
  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    if (!ctx) return
    let raf = 0, last = performance.now()
    let w = 0, h = 0
    const resize = () => {
      const r = cv.getBoundingClientRect(); const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = r.width; h = r.height; cv.width = Math.max(1, Math.floor(w * dpr)); cv.height = Math.max(1, Math.floor(h * dpr)); ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const ro = new ResizeObserver(() => { resize(); if (still) draw(ctx, w, h, 0, 0) })
    ro.observe(cv)
    const loop = (n: number) => { const dt = Math.min(0.05, (n - last) / 1000); last = n; draw(ctx, w, h, n / 1000, dt); raf = requestAnimationFrame(loop) }
    if (active && !still) raf = requestAnimationFrame(loop)
    else draw(ctx, w, h, 0, 0)
    return () => { cancelAnimationFrame(raf); ro.disconnect() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, still, ...deps])
}

/** Hero: an EEG trace that morphs into sound-wave bars, with particles riding the path. */
export function HeroWave({ className = '' }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const active = useActive(ref)
  const reduce = usePrefersReducedMotion()
  const parts = useRef(Array.from({ length: 46 }, (_, i) => ({ p: mulberry(i + 3)(), v: 0.03 + mulberry(i + 90)() * 0.05, r: 1 + mulberry(i + 50)() * 1.8, o: mulberry(i + 20)() })))
  useCanvas((c, w, h, t, dt) => {
    c.clearRect(0, 0, w, h)
    const mid = h / 2
    const morph = (x: number) => Math.min(1, Math.max(0, (x / w - 0.52) / 0.3)) // 0 = EEG, 1 = bars
    const eeg = (x: number, layer: number) => {
      const u = x / w
      const env = 0.55 + 0.45 * Math.sin(u * 3 + t * 0.4)
      return (Math.sin(u * 38 + t * 2.1 + layer) * 0.5 + Math.sin(u * 17 - t * 1.3 + layer * 2) * 0.35 + Math.sin(u * 83 + t * 3.2) * 0.12) * h * 0.2 * env
    }
    // faint layers
    for (let l = 0; l < 3; l++) {
      c.beginPath()
      for (let x = 0; x <= w; x += 3) { const m = morph(x); const y = mid + eeg(x, l) * (1 - m) + Math.sin(x * 0.02 + t + l) * 6 * m; x === 0 ? c.moveTo(x, y) : c.lineTo(x, y) }
      c.strokeStyle = l === 0 ? '#2B1B16' : l === 1 ? '#80665A' : '#CBB9AC'; c.globalAlpha = l === 0 ? 0.95 : 0.55; c.lineWidth = l === 0 ? 2 : 1.2; c.stroke()
    }
    c.globalAlpha = 1
    // bars
    const bw = 5, gap = 9
    for (let x = w * 0.52; x < w - 8; x += gap + bw) {
      const m = morph(x); if (m <= 0.02) continue
      const u = x / w
      const amp = (Math.sin(u * 30 + t * 2.4) * 0.5 + 0.5) * (0.35 + 0.65 * Math.sin(u * 7 + t) ** 2) * h * 0.34 * m + 4
      c.fillStyle = '#80665A'; c.globalAlpha = 0.3 + 0.7 * m
      c.beginPath(); c.roundRect(x, mid - amp, bw, amp * 2, 3); c.fill()
    }
    c.globalAlpha = 1
    // particles following the primary path
    for (const p of parts.current) {
      p.p = (p.p + p.v * dt) % 1
      const x = p.p * w; const m = morph(x)
      const y = mid + eeg(x, 0) * (1 - m) + Math.sin(x * 0.02 + t) * 6 * m + (m > 0 ? Math.sin(t * 2 + p.o * 9) * 22 * m : 0)
      c.beginPath(); c.arc(x, y, p.r, 0, 6.283); c.fillStyle = p.o > 0.6 ? '#B08968' : '#63463B'; c.globalAlpha = 0.35 + 0.5 * p.o; c.fill()
    }
    c.globalAlpha = 1
  }, active, reduce, ref)
  return <canvas ref={ref} className={className} role="img" aria-label="Animated EEG waveform morphing into sound waves" />
}

/** Small interactive EEG: pointer sets the dominant frequency and amplitude. */
export function InteractiveEeg({ freq, amp, className = '' }: { freq: number; amp: number; className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const active = useActive(ref)
  const reduce = usePrefersReducedMotion()
  const f = useRef({ freq, amp }); f.current = { freq, amp }
  useCanvas((c, w, h, t) => {
    c.clearRect(0, 0, w, h)
    c.strokeStyle = '#E9DED6'; c.lineWidth = 1
    for (let i = 1; i < 4; i++) { c.beginPath(); c.moveTo(0, (h * i) / 4); c.lineTo(w, (h * i) / 4); c.stroke() }
    c.beginPath()
    for (let x = 0; x <= w; x += 2) {
      const s = x / w * 3
      const y = h / 2 + Math.sin(2 * Math.PI * f.current.freq * s + t * 4) * f.current.amp * h * 0.38 + Math.sin(2 * Math.PI * 2.1 * s + t) * h * 0.04
      x === 0 ? c.moveTo(x, y) : c.lineTo(x, y)
    }
    c.strokeStyle = '#2B1B16'; c.lineWidth = 2; c.stroke()
  }, active, reduce, ref, [freq, amp])
  return <canvas ref={ref} className={className} role="img" aria-label={`Synthetic illustration of a ${freq.toFixed(0)} hertz rhythm`} />
}

export interface EegFrame { channels: Record<string, number[]>; fs: number; pollMs: number; stepS: number; seq: number }

/** Multi-channel scrolling EEG fed by real API windows (smooth scroll between 1s polls). */
export function EegCanvas({ frame, order, quality, className = '' }: { frame: EegFrame | null; order: string[]; quality?: number[]; className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const active = useActive(ref)
  const reduce = usePrefersReducedMotion()
  const st = useRef<{ prev: Record<string, number[]> | null; cur: Record<string, number[]> | null; at: number; seq: number; scale: Record<string, number>; frame: EegFrame | null }>({ prev: null, cur: null, at: 0, seq: -1, scale: {}, frame: null })
  if (frame && frame.seq !== st.current.seq) {
    st.current.prev = st.current.cur; st.current.cur = frame.channels; st.current.at = performance.now(); st.current.seq = frame.seq; st.current.frame = frame
  }
  const q = useRef(quality); q.current = quality
  useCanvas((c, w, h) => {
    c.clearRect(0, 0, w, h)
    const s = st.current, fr = s.frame
    const lanes = order.length, lh = h / lanes
    const left = 44
    // grid (seconds)
    c.strokeStyle = '#E9DED6'; c.lineWidth = 1
    for (let i = 0; i <= 4; i++) { const x = left + ((w - left) * i) / 4; c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke() }
    order.forEach((ch, li) => {
      const cy = lh * li + lh / 2
      c.strokeStyle = '#F5EFEA'; c.beginPath(); c.moveTo(left, cy); c.lineTo(w, cy); c.stroke()
      c.fillStyle = '#63463B'; c.font = '500 11px "JetBrains Mono", monospace'; c.textBaseline = 'middle'; c.fillText(ch, 6, cy - 7)
      const qv = q.current?.[li]
      if (qv != null) { c.fillStyle = '#E9DED6'; c.fillRect(6, cy + 4, 26, 4); c.fillStyle = qv > 0.7 ? '#2B1B16' : qv > 0.4 ? '#B08968' : '#80665A'; c.fillRect(6, cy + 4, 26 * Math.min(1, qv), 4) }
      if (!fr || !s.cur) return
      const cur = s.cur[ch]; if (!cur) return
      const prev = s.prev?.[ch]
      const delta = Math.round(fr.stepS * fr.fs)
      const prog = reduce ? 1 : Math.min(1, (performance.now() - s.at) / fr.pollMs)
      // build display: prev window then the new tail; viewport slides by prog*delta
      let buf: number[]; let off: number
      if (prev && prev.length === cur.length && delta > 0 && delta < cur.length) { buf = prev.concat(cur.slice(cur.length - delta)); off = prog * delta } else { buf = cur; off = 0 }
      const n = cur.length
      // autoscale (slow-moving)
      let mx = 1e-6; for (let i = 0; i < n; i += 2) { const v = Math.abs(buf[Math.floor(off) + i] ?? 0); if (v > mx) mx = v }
      const sc = (s.scale[ch] = s.scale[ch] ? s.scale[ch] + 0.05 * (mx - s.scale[ch]) : mx)
      const k = (lh * 0.42) / Math.max(sc, 1)
      c.beginPath()
      for (let i = 0; i < n; i++) {
        const idx = off + i; const i0 = Math.floor(idx); const fr2 = idx - i0
        const v = (buf[i0] ?? 0) * (1 - fr2) + (buf[i0 + 1] ?? buf[i0] ?? 0) * fr2
        const x = left + ((w - left) * i) / (n - 1); const y = cy - v * k
        i === 0 ? c.moveTo(x, y) : c.lineTo(x, y)
      }
      c.strokeStyle = ['#2B1B16', '#4A3028', '#63463B', '#80665A'][li % 4]; c.lineWidth = 1.5; c.lineJoin = 'round'; c.stroke()
    })
  }, active, false, ref, [order.join(',')])
  return <canvas ref={ref} className={className} role="img" aria-label="Live multi-channel EEG waveform" />
}
