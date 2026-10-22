import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Logo } from './Logo'
import { useApp } from '../store/app'

const links = [
  { to: '/lab', label: 'Lab' },
  { to: '/history', label: 'History' },
  { to: '/guide', label: 'NeuroGuide' },
]

export function Navbar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const loc = useLocation()
  const { user, logout } = useApp()
  useEffect(() => setOpen(false), [loc.pathname])
  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 8)
    h(); window.addEventListener('scroll', h, { passive: true })
    return () => window.removeEventListener('scroll', h)
  }, [])
  const cls = ({ isActive }: { isActive: boolean }) => `rounded-full px-3.5 py-1.5 text-sm transition ${isActive ? 'bg-espresso-950 text-sand-50' : 'text-espresso-800 hover:bg-sand-200'}`
  return (
    <header className={`sticky top-0 z-50 transition ${scrolled ? 'border-b border-sand-200 bg-sand-50/90 backdrop-blur' : 'bg-transparent'}`}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <div className="container-x flex h-[68px] items-center justify-between">
        <Logo />
        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          {links.map((l) => <NavLink key={l.to} to={l.to} className={cls}>{l.label}</NavLink>)}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          {user && <span className="font-mono text-[11px] text-espresso-600">{user.is_demo ? 'Guest' : user.display_name}</span>}
          {user && !user.is_demo
            ? <button className="btn-ghost" onClick={() => void logout()}>Sign out</button>
            : <Link to="/login" className="btn-ghost">Sign in</Link>}
          <Link to="/lab" className="btn-primary">Open Lab</Link>
        </div>
        <button type="button" className="rounded-lg p-2 md:hidden" aria-label="Toggle menu" aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen(!open)}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2B1B16" strokeWidth="1.8" strokeLinecap="round">{open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 8h16M4 16h16" />}</svg>
        </button>
      </div>
      {open && (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-sand-200 bg-sand-50 px-5 pb-5 pt-3 md:hidden">
          <div className="flex flex-col gap-1">
            {links.map((l) => <NavLink key={l.to} to={l.to} className={cls}>{l.label}</NavLink>)}
            <NavLink to="/login" className={cls}>Sign in</NavLink>
          </div>
        </nav>
      )}
    </header>
  )
}

export function Footer() {
  return (
    <footer className="dark-section mt-24 bg-espresso-950 text-sand-200">
      <div className="container-x grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Logo inverse />
          <p className="mt-5 max-w-sm font-display text-lg text-sand-100">Brainwave → Emotion → Music</p>
          <p className="mt-2 text-sm text-sand-300">Built with AI, neuroscience &amp; creativity.</p>
        </div>
        <nav aria-label="Footer" className="text-sm">
          <p className="label-mono !text-sand-300">Explore</p>
          <ul className="mt-3 space-y-2">
            <li><Link className="hover:text-white" to="/lab">Brainwave Lab</Link></li>
            <li><Link className="hover:text-white" to="/history">Session history</Link></li>
            <li><Link className="hover:text-white" to="/guide">NeuroGuide</Link></li>
            <li><Link className="hover:text-white" to="/login">Account</Link></li>
          </ul>
        </nav>
        <div className="text-sm">
          <p className="label-mono !text-sand-300">Note</p>
          <p className="mt-3 text-sand-300">EEG-derived emotional states are estimates, not medical diagnoses.</p>
        </div>
      </div>
      <div className="border-t border-espresso-800">
        <div className="container-x flex flex-col items-start justify-between gap-2 py-5 font-mono text-[11px] text-sand-300 sm:flex-row">
          <span>NeuroSonic AI</span>
          <span>Created by Divyanshi.</span>
        </div>
      </div>
    </footer>
  )
}
