import { motion, useReducedMotion } from 'framer-motion'

const E = '#2B1B16', M = '#80665A', S = '#CBB9AC', P = '#E9DED6'

/** Top-down head with the 4 Muse-style electrodes: TP9, AF7, AF8, TP10. */
export function HeadbandDiagram({ className = '', quality }: { className?: string; quality?: number[] }) {
  const pts = [
    { n: 'TP9', x: 38, y: 142 }, { n: 'AF7', x: 62, y: 62 }, { n: 'AF8', x: 138, y: 62 }, { n: 'TP10', x: 162, y: 142 },
  ]
  return (
    <svg viewBox="0 0 200 220" className={className} role="img" aria-label="Headband electrode positions: TP9, AF7, AF8, TP10">
      <path d="M92 14l8-10 8 10" fill="none" stroke={M} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <ellipse cx="100" cy="112" rx="72" ry="86" fill={P} stroke={E} strokeWidth="2" />
      <ellipse cx="28" cy="116" rx="9" ry="20" fill={P} stroke={E} strokeWidth="2" />
      <ellipse cx="172" cy="116" rx="9" ry="20" fill={P} stroke={E} strokeWidth="2" />
      <path d="M38 142 C 50 56, 150 56, 162 142" fill="none" stroke={E} strokeWidth="5" strokeLinecap="round" opacity=".85" />
      <path d="M60 80 C 80 36, 120 36, 140 80" fill="none" stroke={S} strokeWidth="1.2" strokeDasharray="3 4" />
      {pts.map((p, i) => (
        <g key={p.n}>
          <circle cx={p.x} cy={p.y} r="12" fill="#FAF8F6" stroke={E} strokeWidth="2" />
          <circle cx={p.x} cy={p.y} r="5" fill={quality ? `rgba(43,27,22,${0.3 + 0.7 * (quality[i] ?? 1)})` : E} />
          <text x={p.x} y={p.y + (p.y < 100 ? -18 : 28)} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" fill={E} stroke="#FAF8F6" strokeWidth="3" paintOrder="stroke">{p.n}</text>
        </g>
      ))}
      <text x="100" y="118" textAnchor="middle" fontFamily="Fraunces, serif" fontStyle="italic" fontSize="12" fill={M}>frontal · temporal</text>
    </svg>
  )
}

export function Headphones({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 180" className={className} aria-hidden="true">
      <path d="M30 110 V92 C30 48 62 22 100 22 S170 48 170 92 V110" fill="none" stroke={E} strokeWidth="7" strokeLinecap="round" />
      <path d="M44 100 V90 C44 58 68 38 100 38 S156 58 156 90 V100" fill="none" stroke={S} strokeWidth="2" strokeDasharray="2 5" />
      <rect x="18" y="100" width="34" height="62" rx="14" fill={E} />
      <rect x="148" y="100" width="34" height="62" rx="14" fill={E} />
      <rect x="26" y="110" width="18" height="42" rx="9" fill={M} />
      <rect x="156" y="110" width="18" height="42" rx="9" fill={M} />
      {[78, 90, 102, 114, 126].map((x, i) => <rect key={x} x={x - 2} y={90 - [10, 22, 34, 22, 10][i] / 2 + 20} width="4" height={[10, 22, 34, 22, 10][i]} rx="2" fill={M} />)}
    </svg>
  )
}

export function BrainContour({ className = '' }: { className?: string }) {
  const reduce = useReducedMotion()
  return (
    <svg viewBox="0 0 240 200" className={className} role="img" aria-label="Brain hemisphere contour with an EEG trace">
      <path d="M120 16C74 12 30 40 28 86c-1 22 8 32 8 32s-14 14-8 34c6 20 30 26 48 22 12 12 38 16 52 4" fill="none" stroke={E} strokeWidth="3" strokeLinecap="round" />
      <path d="M80 60c12-14 30-10 36 4M52 100c14-8 28 0 30 12M96 120c10-10 24-6 24 8M70 150c6-12 22-14 32-4" fill="none" stroke={S} strokeWidth="2" strokeLinecap="round" />
      <motion.path d="M18 100h40l10-28 14 62 16-80 12 56 10-20h20" fill="none" stroke={E} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"
        initial={reduce ? false : { pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.8, ease: 'easeInOut' }} />
      {[176, 192, 208, 224].map((x, i) => {
        const h = [30, 74, 50, 24][i]
        return (
          <motion.g key={x} style={{ transformBox: 'fill-box', transformOrigin: 'center' }} initial={reduce ? false : { scaleY: 0.1 }} whileInView={{ scaleY: 1 }} viewport={{ once: true }} transition={{ delay: 1 + i * 0.12, type: 'spring' }}>
            <rect x={x - 3} y={100 - h / 2} width="6" height={h} rx="3" fill={M} />
          </motion.g>
        )
      })}
    </svg>
  )
}

const STEPS = [
  { t: 'EEG signal', d: '4 channels · 5 bands', icon: <path d="M3 12h4l2-6 3 12 3-9 2 3h4" /> },
  { t: 'Emotion AI', d: 'Valence · arousal · focus', icon: <><circle cx="12" cy="12" r="8" /><path d="M8.5 14.5c1.8 2 5.2 2 7 0M9 9.5h.01M15 9.5h.01" /></> },
  { t: 'Personalized music', d: 'Tempo · key · texture', icon: <><path d="M9 18V6l10-2v12" /><circle cx="6.5" cy="18" r="2.5" /><circle cx="16.5" cy="16" r="2.5" /></> },
]

export function PipelineStrip({ dark = false }: { dark?: boolean }) {
  return (
    <ol aria-label="How NeuroSonic works" className="grid gap-3 sm:grid-cols-[1fr_auto_1fr_auto_1fr] sm:items-center">
      {STEPS.flatMap((s, i) => {
        const card = (
          <li key={s.t} className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${dark ? 'border-espresso-700 bg-espresso-900' : 'border-sand-200 bg-white/80 shadow-soft'}`}>
            <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${dark ? 'bg-espresso-800' : 'bg-sand-200'}`}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={dark ? '#E9DED6' : E} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{s.icon}</svg>
            </span>
            <span><span className={`block font-display text-base ${dark ? 'text-sand-50' : 'text-espresso-950'}`}><span className="mr-1.5 font-mono text-[10px] text-clay">0{i + 1}</span>{s.t}</span><span className={`block text-xs ${dark ? 'text-sand-300' : 'text-espresso-600'}`}>{s.d}</span></span>
          </li>
        )
        return i < 2 ? [card, <li key={`a${i}`} aria-hidden className="hidden text-center font-mono text-clay sm:block">→</li>] : [card]
      })}
    </ol>
  )
}

const ARCH = ['EEG', 'Signal processing', 'Feature extraction', 'Emotion model', 'LLM / NLP', 'RAG', 'Music engine', 'Audio']
const ARCH_SUB = ['TP9 · AF7 · AF8 · TP10', 'filter · window · quality', 'band power · FAA · PSD', 'valence · arousal · focus', 'text → intent', 'NeuroGuide sources', 'tempo · key · texture', 'rendered WAV']

export function ArchitectureDiagram() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {ARCH.map((n, i) => (
        <div key={n} className="relative rounded-2xl border border-espresso-700 bg-espresso-900 p-4">
          <p className="font-mono text-[10px] text-clay">{String(i + 1).padStart(2, '0')}</p>
          <p className="mt-1 font-display text-lg text-sand-50">{n}</p>
          <p className="mt-1 text-xs text-sand-300">{ARCH_SUB[i]}</p>
          {i < ARCH.length - 1 && <span aria-hidden className="absolute -right-2.5 top-1/2 z-10 hidden -translate-y-1/2 font-mono text-sand-300 lg:block">{i % 4 === 3 ? '' : '→'}</span>}
        </div>
      ))}
    </div>
  )
}
