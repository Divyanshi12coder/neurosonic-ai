import { useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { clamp } from '../../lib/util'

/** Signature slider: CURRENT STATE <-> TARGET STATE. Pointer + full keyboard support. */
export function MoodSlider({ value, onChange, left, right, disabled = false }: { value: number; onChange: (v: number) => void; left: string; right: string; disabled?: boolean }) {
  const track = useRef<HTMLDivElement>(null)
  const set = useCallback((clientX: number) => {
    const r = track.current?.getBoundingClientRect(); if (!r) return
    onChange(clamp((clientX - r.left) / r.width))
  }, [onChange])
  const onKey = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 0.1 : 0.02
    const map: Record<string, number | undefined> = { ArrowRight: value + step, ArrowUp: value + step, ArrowLeft: value - step, ArrowDown: value - step, PageUp: value + 0.1, PageDown: value - 0.1, Home: 0, End: 1 }
    if (e.key in map && map[e.key] !== undefined) { e.preventDefault(); onChange(clamp(map[e.key]!)) }
  }
  return (
    <div className={disabled ? 'opacity-45' : ''}>
      <div className="mb-3 flex items-end justify-between gap-3 font-display text-lg tracking-wide sm:text-2xl">
        <span className="max-w-[40%] truncate text-espresso-950" style={{ opacity: 1 - value * 0.55 }}>{left}</span>
        <span aria-hidden className="mb-1 flex-1 border-b border-dashed border-sand-300" />
        <span className="max-w-[40%] truncate text-right text-espresso-950" style={{ opacity: 0.45 + value * 0.55 }}>{right}</span>
      </div>
      <div ref={track} className="relative h-10 touch-none select-none"
        onPointerDown={(e) => { if (disabled) return; (e.target as Element).setPointerCapture?.(e.pointerId); set(e.clientX) }}
        onPointerMove={(e) => { if (!disabled && e.buttons === 1) set(e.clientX) }}>
        <div className="absolute left-0 right-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-sand-200" />
        <motion.div className="absolute left-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-gradient-to-r from-espresso-600 to-espresso-950" animate={{ width: `${value * 100}%` }} transition={{ duration: 0.12 }} />
        {[0, 0.25, 0.5, 0.75, 1].map((t) => <span key={t} aria-hidden className="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-sand-300" style={{ left: `${t * 100}%` }} />)}
        <div role="slider" tabIndex={disabled ? -1 : 0} aria-label="Mood transformation: from current state to target state" aria-valuemin={0} aria-valuemax={100}
          aria-valuenow={Math.round(value * 100)} aria-valuetext={`${Math.round(value * 100)} percent of the way from ${left} to ${right}`} aria-disabled={disabled} onKeyDown={onKey}
          className="absolute top-1/2 grid h-9 w-9 -translate-x-1/2 -translate-y-1/2 cursor-grab place-items-center rounded-full border-2 border-sand-50 bg-espresso-950 shadow-lift active:cursor-grabbing"
          style={{ left: `${value * 100}%` }}>
          <span className="font-mono text-[10px] text-sand-50">{Math.round(value * 100)}</span>
        </div>
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] uppercase tracking-wider text-espresso-600"><span>match</span><span>halfway</span><span>full shift</span></div>
    </div>
  )
}
