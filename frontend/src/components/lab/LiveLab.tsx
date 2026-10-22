import { memo, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BANDS, type AnalysisOut, type Dim } from '../../lib/api'
import { clamp, fmt } from '../../lib/util'
import { EegCanvas, type EegFrame } from '../Canvases'
import { Bar, ModelBadge, Skeleton } from '../ui'

export type Smooth = Record<Dim | 'confidence', number>

const BAND_RANGE: Record<string, string> = { delta: '1–4 Hz', theta: '4–8 Hz', alpha: '8–13 Hz', beta: '13–30 Hz', gamma: '30–45 Hz' }
const BAND_NOTE: Record<string, string> = { delta: 'deep rest', theta: 'drowsy / inward', alpha: 'relaxed wakefulness', beta: 'active thinking', gamma: 'high-frequency' }

function Gauge({ label, value, hint }: { label: string; value: number; hint: string }) {
  const r = 34, c = Math.PI * r
  const v = clamp(value)
  return (
    <div className="rounded-xl border border-sand-200 bg-sand-50 p-3 text-center" title={hint}>
      <svg viewBox="0 0 90 56" className="mx-auto w-full max-w-[110px]" role="img" aria-label={`${label} ${Math.round(v * 100)} percent`}>
        <path d="M11 48 A34 34 0 0 1 79 48" fill="none" stroke="#E9DED6" strokeWidth="7" strokeLinecap="round" />
        <motion.path d="M11 48 A34 34 0 0 1 79 48" fill="none" stroke="#2B1B16" strokeWidth="7" strokeLinecap="round" strokeDasharray={c}
          animate={{ strokeDashoffset: c * (1 - v) }} initial={{ strokeDashoffset: c }} transition={{ type: 'spring', stiffness: 90, damping: 18 }} />
        <text x="45" y="46" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="13" fontWeight="500" fill="#2B1B16">{Math.round(v * 100)}</text>
      </svg>
      <p className="label-mono -mt-1">{label}</p>
    </div>
  )
}

export const Gauges = memo(function Gauges({ s }: { s: Smooth | null }) {
  const items: [string, Dim, string][] = [
    ['Valence', 'valence', 'Negative ↔ positive feeling (estimated)'],
    ['Arousal', 'arousal', 'Low ↔ high activation (estimated)'],
    ['Focus', 'focus', 'Attentional engagement (estimated)'],
    ['Stress', 'stress', 'Stress tendency (estimated)'],
    ['Calmness', 'calmness', 'Relaxed settledness (estimated)'],
  ]
  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
      {items.map(([l, k, h]) => <Gauge key={k} label={l} value={s?.[k] ?? 0} hint={h} />)}
    </div>
  )
})

export const LiveLab = memo(function LiveLab({ data, smooth, frame, rel }: { data: AnalysisOut | null; smooth: Smooth | null; frame: EegFrame | null; rel: Record<string, number> | null }) {
  const psd = useMemo(() => {
    if (!data) return []
    const { freqs, power } = data.features.psd
    const mx = Math.max(...power, 1e-9)
    return freqs.map((f, i) => ({ f, p: power[i] / mx }))
  }, [data])
  const f = data?.features
  const model = data?.emotion.model
  const label = data?.emotion.label ?? ''
  const quad = data?.emotion.quadrant ?? ''
  return (
    <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
      <div className="card overflow-hidden p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sand-200 px-5 py-3">
          <div>
            <p className="label-mono">Current estimated state</p>
            <p className="font-display text-2xl tracking-tight" aria-live="polite">{data ? <>{label.toUpperCase()}<span className="mx-2 text-clay">·</span><span className="text-lg text-espresso-700">{quad.toUpperCase()}</span></> : '—'}</p>
          </div>
          <div className="text-right">
            <ModelBadge label={model?.label as string | undefined} demo={model?.is_demo_baseline !== false} />
            <p className="mt-1 font-mono text-[10px] text-espresso-600">signal quality: {data?.quality.label ?? '—'} ({fmt(data?.quality.overall, 2)})</p>
          </div>
        </div>
        <div className="h-[260px] px-2 py-2 sm:h-[300px]">
          {data ? <EegCanvas frame={frame} order={data.channels} quality={data.quality.per_channel} className="h-full w-full" /> : <Skeleton className="h-full w-full" />}
        </div>
        <div className="grid grid-cols-2 gap-px border-t border-sand-200 bg-sand-200 sm:grid-cols-4">
          {[
            ['Dominant freq', f ? `${fmt(f.dominant_frequency, 1)} Hz` : '—'],
            ['Spectral entropy', fmt(f?.spectral_entropy, 3)],
            ['Frontal α asymmetry', fmt(f?.frontal_alpha_asymmetry, 3)],
            ['θ/β ratio', fmt(f?.ratios?.theta_beta, 2)],
            ['α/β ratio', fmt(f?.ratios?.alpha_beta, 2)],
            ['Engagement β/(α+θ)', fmt(f?.ratios?.engagement, 3)],
            ['Signal variance', f ? `${fmt(f.signal_variance, 1)} µV²` : '—'],
            ['Confidence', data ? `${Math.round((smooth?.confidence ?? 0) * 100)}%` : '—'],
          ].map(([k, v]) => (
            <div key={k} className="bg-white px-4 py-3"><p className="label-mono !text-[10px]">{k}</p><p className="mt-0.5 font-mono text-sm text-espresso-950">{v}</p></div>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        <div className="card p-5">
          <div className="mb-3 flex items-baseline justify-between"><h3 className="font-display text-lg">Frequency bands</h3><span className="label-mono">relative power</span></div>
          <div className="space-y-2.5">
            {BANDS.map((b) => (
              <Bar key={b} label={`${b[0].toUpperCase()}${b.slice(1)} · ${BAND_RANGE[b]}`} value={Math.min(1, (rel?.[b] ?? 0) * 1.6)} right={`${((rel?.[b] ?? 0) * 100).toFixed(1)}% · ${BAND_NOTE[b]}`} tone={b === 'alpha' ? 'clay' : 'dark'} />
            ))}
          </div>
        </div>
        <div className="card p-5">
          <div className="mb-1 flex items-baseline justify-between"><h3 className="font-display text-lg">Power spectrum</h3><span className="label-mono">normalised PSD</span></div>
          <div className="h-36" role="img" aria-label="Power spectral density chart">
            {psd.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={psd} margin={{ top: 6, right: 4, left: -28, bottom: 0 }}>
                  <CartesianGrid stroke="#E9DED6" vertical={false} />
                  <XAxis dataKey="f" type="number" domain={[1, 45]} tick={{ fontSize: 10, fill: '#80665A', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={{ stroke: '#CBB9AC' }} unit="Hz" />
                  <YAxis hide domain={[0, 1]} />
                  <Tooltip formatter={(v: number) => v.toFixed(2)} labelFormatter={(l) => `${l} Hz`} contentStyle={{ borderRadius: 12, border: '1px solid #E9DED6', fontSize: 12 }} />
                  <Area type="monotone" dataKey="p" stroke="#2B1B16" strokeWidth={1.8} fill="#CBB9AC" fillOpacity={0.45} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            ) : <Skeleton className="h-full" />}
          </div>
        </div>
      </div>
    </div>
  )
})
