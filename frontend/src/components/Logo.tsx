import { Link } from 'react-router-dom'

/** Brain-hemisphere contour + EEG trace morphing into sound-wave bars. */
export function LogoMark({ size = 36, inverse = false, className = '' }: { size?: number; inverse?: boolean; className?: string }) {
  const main = inverse ? '#FAF8F6' : '#2B1B16'
  const sub = inverse ? '#CBB9AC' : '#80665A'
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true" className={className}>
      <g strokeLinecap="round" strokeLinejoin="round">
        <path d="M31 9C18 9 9 19 9 32s9 23 22 23" stroke={main} strokeWidth="3" />
        <path d="M9 32h6l4-8 5 17 5-22 4 13h4" stroke={main} strokeWidth="2.6" />
        <path d="M43 26v12M49 18v28M55 24v16" stroke={sub} strokeWidth="3.4" />
      </g>
    </svg>
  )
}

export function Logo({ inverse = false, to = '/' }: { inverse?: boolean; to?: string }) {
  return (
    <Link to={to} aria-label="NeuroSonic AI home" className="inline-flex items-center gap-2.5">
      <LogoMark inverse={inverse} />
      <span className="leading-none">
        <span className={`block font-display text-[1.35rem] font-medium tracking-tight ${inverse ? 'text-sand-50' : 'text-espresso-950'}`}>NeuroSonic <span className="font-light italic">AI</span></span>
        <span className={`mt-1 block font-mono text-[9px] uppercase tracking-[.16em] ${inverse ? 'text-sand-300' : 'text-espresso-600'}`}>Brainwave → Emotion → Music</span>
      </span>
    </Link>
  )
}
