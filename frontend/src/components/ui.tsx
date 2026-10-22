import { Component, useEffect, useId, useRef, useState, type ErrorInfo, type ReactNode } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'
import { Link } from 'react-router-dom'

export function Reveal({ children, delay = 0, y = 24, className = '' }: { children: ReactNode; delay?: number; y?: number; className?: string }) {
  const reduce = useReducedMotion()
  return (
    <motion.div className={className} initial={reduce ? false : { opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }} transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  )
}

export function Counter({ to, decimals = 0, suffix = '' }: { to: number; decimals?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const reduce = useReducedMotion()
  const [v, setV] = useState(0)
  useEffect(() => {
    if (!inView) return
    if (reduce) { setV(to); return }
    let raf = 0
    const t0 = performance.now()
    const tick = (n: number) => {
      const p = Math.min(1, (n - t0) / 1400)
      setV(to * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, to, reduce])
  return <span ref={ref}>{v.toFixed(decimals)}{suffix}</span>
}

export function Accordion({ items }: { items: { q: string; a: ReactNode }[] }) {
  const [open, setOpen] = useState<number | null>(0)
  const id = useId()
  return (
    <div className="divide-y divide-sand-200 rounded-2xl border border-sand-200 bg-white">
      {items.map((it, i) => (
        <div key={i}>
          <h3>
            <button type="button" aria-expanded={open === i} aria-controls={`${id}-${i}`} onClick={() => setOpen(open === i ? null : i)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left font-display text-lg text-espresso-950">
              {it.q}
              <span aria-hidden className={`font-mono text-xl text-espresso-600 transition-transform ${open === i ? 'rotate-45' : ''}`}>+</span>
            </button>
          </h3>
          <motion.div id={`${id}-${i}`} role="region" initial={false} animate={{ height: open === i ? 'auto' : 0, opacity: open === i ? 1 : 0 }}
            transition={{ duration: 0.3 }} className="overflow-hidden">
            <div className="px-5 pb-5 text-sm leading-relaxed text-espresso-700">{it.a}</div>
          </motion.div>
        </div>
      ))}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) { return <div className={`skeleton ${className}`} aria-hidden="true" /> }

export function SectionHead({ eyebrow, title, sub, dark = false, center = false }: { eyebrow: string; title: ReactNode; sub?: ReactNode; dark?: boolean; center?: boolean }) {
  return (
    <div className={`mb-10 max-w-3xl ${center ? 'mx-auto text-center' : ''}`}>
      <p className={`eyebrow ${dark ? '!text-sand-300' : ''}`}>{eyebrow}</p>
      <h2 className={`h-display mt-3 text-3xl sm:text-4xl lg:text-5xl ${dark ? '!text-sand-50' : ''}`}>{title}</h2>
      {sub && <p className={`mt-4 text-base leading-relaxed ${dark ? 'text-sand-200' : 'text-espresso-700'}`}>{sub}</p>}
    </div>
  )
}

export const DISCLAIMER = 'This project is an experimental AI research/product prototype. EEG-derived emotional states are estimates and should not be interpreted as medical diagnoses or clinical assessments.'

export function Disclaimer({ dark = false, className = '' }: { dark?: boolean; className?: string }) {
  return (
    <p role="note" className={`rounded-xl border px-4 py-3 text-xs leading-relaxed ${dark ? 'border-espresso-700 bg-espresso-900 text-sand-200' : 'border-sand-300 bg-sand-100 text-espresso-700'} ${className}`}>
      <span className="font-mono uppercase tracking-wider">Note · </span>{DISCLAIMER}
    </p>
  )
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }: { title?: string; message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card mx-auto max-w-xl p-6 text-center">
      <p className="font-display text-xl">{title}</p>
      <p className="mt-2 text-sm text-espresso-700">{message}</p>
      {onRetry && <button className="btn-primary mt-4" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function Empty({ title, children, cta }: { title: string; children?: ReactNode; cta?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-sand-300 bg-sand-100/60 p-8 text-center">
      <p className="font-display text-xl text-espresso-900">{title}</p>
      {children && <p className="mx-auto mt-2 max-w-md text-sm text-espresso-700">{children}</p>}
      {cta && <div className="mt-4">{cta}</div>}
    </div>
  )
}

export function ModelBadge({ label, demo = true }: { label?: string; demo?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-sand-300 bg-sand-100 px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-espresso-700" title="The emotion model is trained on synthetic data to demonstrate the pipeline.">
      <span className={`h-1.5 w-1.5 rounded-full ${demo ? 'bg-clay' : 'bg-espresso-700'}`} />
      {label ?? 'Model'}
    </span>
  )
}

export function Bar({ value, label, right, tone = 'dark' }: { value: number; label: string; right?: ReactNode; tone?: 'dark' | 'clay' | 'light' }) {
  const bg = tone === 'dark' ? 'bg-espresso-900' : tone === 'clay' ? 'bg-clay' : 'bg-sand-300'
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span className="text-espresso-800">{label}</span>
        <span className="font-mono text-espresso-600">{right}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-sand-200" role="img" aria-label={`${label} ${Math.round(value * 100)}%`}>
        <motion.div className={`h-full rounded-full ${bg}`} animate={{ width: `${Math.min(1, Math.max(0, value)) * 100}%` }} transition={{ type: 'spring', stiffness: 120, damping: 20 }} />
      </div>
    </div>
  )
}

interface EBState { err: Error | null }
export class ErrorBoundary extends Component<{ children: ReactNode }, EBState> {
  state: EBState = { err: null }
  static getDerivedStateFromError(err: Error) { return { err } }
  componentDidCatch(e: Error, i: ErrInfo) { console.error('UI error', e, i.componentStack) }
  render() {
    if (this.state.err) {
      return (
        <div className="container-x py-24">
          <ErrorState title="This view hit an unexpected error" message={this.state.err.message} onRetry={() => this.setState({ err: null })} />
          <p className="mt-4 text-center text-sm"><Link className="underline" to="/">Return home</Link></p>
        </div>
      )
    }
    return this.props.children
  }
}
type ErrInfo = ErrorInfo
