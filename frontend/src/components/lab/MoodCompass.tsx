import { memo } from 'react'
import { motion } from 'framer-motion'
import type { Plan, StatePoint } from '../../lib/api'
import { clamp } from '../../lib/util'

const X = (v = 0.5) => 40 + clamp(v) * 320
const Y = (a = 0.5) => 360 - clamp(a) * 320
const spring = { type: 'spring' as const, stiffness: 90, damping: 16 }

function Dot({ p, label, kind }: { p?: StatePoint; label: string; kind: 'current' | 'target' | 'music' }) {
  if (!p) return null
  const cx = X(p.valence), cy = Y(p.arousal)
  const style = kind === 'current' ? { fill: '#2B1B16', stroke: '#FAF8F6' } : kind === 'target' ? { fill: '#FAF8F6', stroke: '#2B1B16' } : { fill: '#B08968', stroke: '#FAF8F6' }
  const flip = cx > 280
  return (
    <motion.g initial={false} animate={{ x: cx, y: cy }} transition={spring}>
      {kind === 'music' && <circle r="18" fill="#B08968" opacity=".18" />}
      <circle r={kind === 'music' ? 8 : 9} {...style} strokeWidth={kind === 'target' ? 2.5 : 2.5} />
      <text x={flip ? -14 : 14} y="4" textAnchor={flip ? 'end' : 'start'} fontFamily="JetBrains Mono, monospace" fontSize="10.5" fill="#2B1B16" fontWeight="500" style={{ paintOrder: 'stroke' }} stroke="#FAF8F6" strokeWidth="3">{label}</text>
    </motion.g>
  )
}

export const MoodCompass = memo(function MoodCompass({ plan, className = '' }: { plan?: Plan | null; className?: string }) {
  const traj = (plan?.trajectory ?? []).map((p) => `${X(p.valence)},${Y(p.arousal)}`)
  return (
    <svg viewBox="0 0 400 400" className={className} role="img"
      aria-label={plan ? `Mood compass. Current valence ${Math.round((plan.current.valence ?? 0) * 100)} percent, arousal ${Math.round((plan.current.arousal ?? 0) * 100)} percent.` : 'Mood compass'}>
      <rect x="40" y="40" width="320" height="320" rx="20" fill="#FAF8F6" stroke="#CBB9AC" />
      <rect x="200" y="40" width="160" height="160" fill="#F5EFEA" opacity=".9" rx="0" />
      <rect x="40" y="200" width="160" height="160" fill="#F5EFEA" opacity=".9" />
      {[0.25, 0.5, 0.75].map((g) => <g key={g} stroke="#E9DED6"><line x1={X(g)} x2={X(g)} y1="40" y2="360" /><line y1={Y(g)} y2={Y(g)} x1="40" x2="360" /></g>)}
      <line x1="200" x2="200" y1="40" y2="360" stroke="#CBB9AC" /><line y1="200" y2="200" x1="40" x2="360" stroke="#CBB9AC" />
      {[['TENSE · AGITATED', 52, 62, 'start'], ['EXCITED · JOYFUL', 348, 62, 'end'], ['SAD · DROWSY', 52, 350, 'start'], ['CALM · CONTENT', 348, 350, 'end']].map(([t, x, y, a]) => (
        <text key={t as string} x={x as number} y={y as number} textAnchor={a as 'start' | 'end'} fontFamily="JetBrains Mono, monospace" fontSize="9.5" letterSpacing="1.4" fill="#80665A">{t}</text>
      ))}
      <text x="200" y="388" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" letterSpacing="1.6" fill="#63463B">VALENCE → positive</text>
      <text transform="translate(14 200) rotate(-90)" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="10" letterSpacing="1.6" fill="#63463B">AROUSAL → high</text>
      {traj.length > 1 && <motion.polyline key={traj.join('|')} points={traj.join(' ')} fill="none" stroke="#80665A" strokeWidth="1.8" strokeDasharray="5 5" strokeLinecap="round" strokeLinejoin="round"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }} />}
      {(plan?.trajectory ?? []).map((p, i, a) => (
        <motion.g key={i} initial={false} animate={{ x: X(p.valence), y: Y(p.arousal) }} transition={spring}>
          <circle r="7" fill="#E9DED6" stroke="#80665A" strokeWidth="1.2" />
          <text y="3.3" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize="8.5" fill="#2B1B16">{i + 1 <= a.length ? i + 1 : ''}</text>
        </motion.g>
      ))}
      <Dot p={plan?.target} label="TARGET" kind="target" />
      <Dot p={plan?.music} label="MUSIC" kind="music" />
      <Dot p={plan?.current} label="NOW" kind="current" />
    </svg>
  )
})
