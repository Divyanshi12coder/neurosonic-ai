import { memo, useId, useMemo } from 'react'
import { mulberry } from '../lib/util'

const DEFAULT_PALETTE = ['#2B1B16', '#4A3028', '#63463B', '#80665A', '#CBB9AC', '#E9DED6']
const hash = (s: string) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) } return h >>> 0 }

export interface ArtProps { seed?: number | string; palette?: string[]; energy?: number; brightness?: number; valence?: number; className?: string; rounded?: boolean; title?: string }

/** Deterministic generative cover art: same seed + profile => same image. Palette tones only. */
export const Artwork = memo(function Artwork({ seed = 1, palette, energy = 0.5, brightness = 0.5, valence = 0.5, className = '', rounded = true, title = 'Generated album artwork' }: ArtProps) {
  const uid = useId().replace(/:/g, '')
  const s = typeof seed === 'string' ? hash(seed) : seed
  const pal = palette && palette.length >= 4 ? palette : DEFAULT_PALETTE
  const shapes = useMemo(() => {
    const r = mulberry(s)
    const dark = brightness < 0.5
    const bg = dark ? pal[0] : pal[pal.length - 1]
    const n = 5 + Math.round(energy * 6)
    const arcs = Array.from({ length: n }, (_, i) => {
      const rad = 18 + i * (88 / n) + r() * 6
      const a0 = r() * Math.PI * 2
      const span = Math.PI * (0.5 + r() * 1.2)
      const cx = 100 + (r() - 0.5) * 60, cy = 100 + (r() - 0.5) * 60
      const x1 = cx + rad * Math.cos(a0), y1 = cy + rad * Math.sin(a0)
      const x2 = cx + rad * Math.cos(a0 + span), y2 = cy + rad * Math.sin(a0 + span)
      return { d: `M${x1.toFixed(1)} ${y1.toFixed(1)} A${rad.toFixed(1)} ${rad.toFixed(1)} 0 ${span > Math.PI ? 1 : 0} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`, w: 1 + r() * (2 + energy * 8), c: pal[1 + Math.floor(r() * (pal.length - 1))], o: 0.45 + r() * 0.5 }
    })
    const bars = Array.from({ length: 18 }, (_, i) => ({ x: 22 + i * 9.6, h: 6 + (Math.sin(i * (0.4 + energy) + s % 7) * 0.5 + 0.5) * (14 + energy * 40) }))
    const orb = { cx: 40 + r() * 120, cy: 40 + r() * (valence > 0.5 ? 50 : 100), r: 14 + r() * 26 }
    return { bg, arcs, bars, orb, dark }
  }, [s, pal, energy, brightness, valence])
  return (
    <svg viewBox="0 0 200 200" role="img" aria-label={title} className={`${className} ${rounded ? 'rounded-2xl' : ''}`} preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id={`g${uid}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={shapes.dark ? pal[1] : pal[pal.length - 2]} stopOpacity=".9" /><stop offset="1" stopColor={shapes.bg} /></linearGradient>
        <clipPath id={`c${uid}`}><rect width="200" height="200" /></clipPath>
      </defs>
      <g clipPath={`url(#c${uid})`}>
        <rect width="200" height="200" fill={shapes.bg} />
        <rect width="200" height="200" fill={`url(#g${uid})`} />
        <circle cx={shapes.orb.cx} cy={shapes.orb.cy} r={shapes.orb.r} fill={shapes.dark ? pal[pal.length - 2] : pal[2]} opacity=".85" />
        {shapes.arcs.map((a, i) => <path key={i} d={a.d} fill="none" stroke={a.c} strokeWidth={a.w} strokeLinecap="round" opacity={a.o} />)}
        <g transform="translate(0 150)" opacity=".8">
          {shapes.bars.map((b, i) => <rect key={i} x={b.x} y={-b.h / 2 + 22} width="4.4" height={b.h} rx="2.2" fill={shapes.dark ? pal[pal.length - 2] : pal[1]} />)}
        </g>
      </g>
    </svg>
  )
})

export function artFor(t: { artwork?: { seed: number; palette: string[]; energy: number; brightness: number; valence: number }; audio_id?: string }) {
  const a = t.artwork
  return { seed: a?.seed ?? t.audio_id ?? 1, palette: a?.palette, energy: a?.energy, brightness: a?.brightness, valence: a?.valence }
}
