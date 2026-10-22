import { useEffect, useRef, useState } from 'react'

export const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v))
export const pct = (v: number | undefined | null) => `${Math.round(clamp(v ?? 0) * 100)}%`
export const fmt = (v: number | undefined | null, d = 2) => (v == null || Number.isNaN(v) ? '—' : v.toFixed(d))
export const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s)

export function usePrefersReducedMotion() {
  const [r, setR] = useState(() => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const m = window.matchMedia('(prefers-reduced-motion: reduce)')
    const h = () => setR(m.matches)
    m.addEventListener('change', h)
    return () => m.removeEventListener('change', h)
  }, [])
  return r
}

/** True while element is on screen and the tab is visible. */
export function useActive(ref: React.RefObject<Element>) {
  const [vis, setVis] = useState(true)
  const [tab, setTab] = useState(() => typeof document === 'undefined' || !document.hidden)
  useEffect(() => {
    const el = ref.current
    if (!el || !('IntersectionObserver' in window)) return
    const io = new IntersectionObserver(([e]) => setVis(e.isIntersecting), { threshold: 0.01 })
    io.observe(el)
    return () => io.disconnect()
  }, [ref])
  useEffect(() => {
    const h = () => setTab(!document.hidden)
    document.addEventListener('visibilitychange', h)
    return () => document.removeEventListener('visibilitychange', h)
  }, [])
  return vis && tab
}

/** Exponential moving average of a numeric record. */
export function ema<T extends Record<string, number>>(prev: T | null, next: T, a = 0.35): T {
  if (!prev) return { ...next }
  const out: Record<string, number> = {}
  for (const k of Object.keys(next)) out[k] = prev[k] == null ? next[k] : prev[k] + a * (next[k] - prev[k])
  return out as T
}

export function useDebounced<T>(v: T, ms: number): T {
  const [d, setD] = useState(v)
  useEffect(() => { const h = setTimeout(() => setD(v), ms); return () => clearTimeout(h) }, [v, ms])
  return d
}

export function useLatest<T>(v: T) { const r = useRef(v); r.current = v; return r }

/** Seeded PRNG */
export function mulberry(seed: number) {
  let a = seed >>> 0
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function downloadText(name: string, text: string, mime = 'text/csv') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }))
  const a = document.createElement('a')
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Client-side sample CSV: 256 Hz, 5 s, 4 channels with alpha-dominant synthetic oscillations. */
export function sampleCsv(seconds = 6, fs = 256): string {
  const rnd = mulberry(11)
  const rows = ['time,TP9,AF7,AF8,TP10']
  for (let i = 0; i < seconds * fs; i++) {
    const t = i / fs
    const v = (f: number, a: number, p: number) => a * Math.sin(2 * Math.PI * f * t + p)
    const row = [0, 1, 2, 3].map((c) => (v(10, 18, c) + v(6, 8, c * 2) + v(20, 4, c) + (rnd() - 0.5) * 8).toFixed(3))
    rows.push(`${t.toFixed(4)},${row.join(',')}`)
  }
  return rows.join('\n')
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return ''
  const d = new Date(iso.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
  const s = (Date.now() - d.getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
