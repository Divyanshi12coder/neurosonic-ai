import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, errMsg, type ChatOut, type ChatSource } from '../lib/api'
import { useApp } from '../store/app'
import { Disclaimer } from '../components/ui'
import { LogoMark } from '../components/Logo'

interface Msg { role: 'user' | 'ai'; text: string; out?: ChatOut; err?: boolean }

function inline(s: string): ReactNode[] {
  return s.split(/(\*\*[^*]+\*\*|\[S\d+\])/g).map((p, i) => {
    if (/^\*\*.+\*\*$/.test(p)) return <strong key={i}>{p.slice(2, -2)}</strong>
    if (/^\[S\d+\]$/.test(p)) return <sup key={i} className="ml-0.5 rounded bg-sand-200 px-1 font-mono text-[10px] text-espresso-800">{p.slice(1, -1)}</sup>
    return <Fragment key={i}>{p}</Fragment>
  })
}
function Lines({ text }: { text: string }) {
  const out: ReactNode[] = []; let list: string[] = []
  const flush = () => { if (list.length) { out.push(<ul key={out.length} className="my-2 list-disc space-y-1.5 pl-5">{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>); list = [] } }
  text.split('\n').forEach((ln) => { if (/^\s*[-•]\s+/.test(ln)) list.push(ln.replace(/^\s*[-•]\s+/, '')); else { flush(); if (ln.trim()) out.push(<p key={out.length} className="my-2">{inline(ln)}</p>) } })
  flush()
  return <>{out}</>
}
/** Split the answer into labelled sections ("**Heading**" lines). */
function sections(answer: string) {
  const parts: { title: string | null; body: string }[] = []
  let cur: { title: string | null; body: string } = { title: null, body: '' }
  for (const ln of answer.split('\n')) {
    const m = ln.match(/^\*\*([^*]+)\*\*\s*(\(.*\))?\s*$/)
    if (m) { if (cur.title || cur.body.trim()) parts.push(cur); cur = { title: m[1] + (m[2] ? ' ' + m[2] : ''), body: '' } } else cur.body += ln + '\n'
  }
  if (cur.title || cur.body.trim()) parts.push(cur)
  return parts
}

function Sources({ sources }: { sources: ChatSource[] }) {
  const [open, setOpen] = useState<string | null>(null)
  if (!sources.length) return null
  return (
    <div className="mt-3 border-t border-sand-200 pt-3">
      <p className="label-mono mb-2">Sources</p>
      <ul className="space-y-1.5">
        {sources.map((s, i) => {
          const id = String(s.id ?? `S${i + 1}`), isOpen = open === id
          return (
            <li key={id} className="rounded-xl border border-sand-200 bg-sand-50">
              <button aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : id)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm">
                <span className="rounded bg-espresso-950 px-1.5 font-mono text-[10px] text-sand-50">{id}</span>
                <span className="flex-1 truncate">{String(s.title ?? 'Source')}{s.heading ? <span className="text-espresso-600"> · {String(s.heading)}</span> : null}</span>
                {s.kind ? <span className="chip !py-0 text-[10px]">{String(s.kind)}</span> : null}
                <span aria-hidden className="font-mono text-espresso-600">{isOpen ? '−' : '+'}</span>
              </button>
              {isOpen && <p className="px-3 pb-3 text-xs leading-relaxed text-espresso-700">{String(s.excerpt ?? s.text ?? s.snippet ?? '')}{s.score != null && <span className="ml-1 font-mono text-espresso-600">(relevance {Number(s.score).toFixed(2)})</span>}</p>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Answer({ m }: { m: Msg }) {
  if (m.err || !m.out) return <p className="text-sm">{m.text}</p>
  const secs = sections(m.out.answer)
  const hasInf = secs.some((s) => /inference/i.test(s.title ?? ''))
  return (
    <div className="text-sm leading-relaxed">
      {secs.map((s, i) => {
        const inf = /inference/i.test(s.title ?? '')
        return (
          <div key={i} className={`my-2 rounded-xl p-3 ${inf ? 'border border-clay/40 bg-sand-100' : ''}`}>
            {s.title && <p className={`label-mono mb-1 ${inf ? '!text-clay' : ''}`}>{inf ? 'Model inference (this session)' : /science/i.test(s.title) ? 'Established science' : s.title}</p>}
            <Lines text={s.body} />
          </div>
        )
      })}
      {!hasInf && m.out.inference.length > 0 && (
        <div className="my-2 rounded-xl border border-clay/40 bg-sand-100 p-3"><p className="label-mono mb-1 !text-clay">Model inference (this session)</p><Lines text={m.out.inference.map((x) => `- ${x}`).join('\n')} /></div>
      )}
      <Sources sources={m.out.sources} />
      <p className="mt-3 font-mono text-[10px] text-espresso-600">{m.out.provider} · {m.out.embedder}</p>
    </div>
  )
}

export default function Guide() {
  const { shared, toast } = useApp()
  const loc = useLocation()
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [sugg, setSugg] = useState<string[]>([])
  const end = useRef<HTMLDivElement>(null)
  const asked = useRef(false)

  useEffect(() => { api.suggestions().then(setSugg).catch(() => setSugg([
    'Why did the system classify my state as high arousal?', 'What does alpha activity represent?', 'Why did you recommend this type of music?', 'How does EEG-based emotion recognition work?'])) }, [])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [msgs, busy])

  const ask = useCallback(async (q: string) => {
    const text = q.trim(); if (!text || busy) return
    setMsgs((m) => [...m, { role: 'user', text }]); setInput(''); setBusy(true)
    try {
      const ctx = shared.emotion ? { emotion: shared.emotion, profile: shared.profile ?? undefined } : null
      const out = await api.chat({ message: text.slice(0, 1000), context: ctx })
      setMsgs((m) => [...m, { role: 'ai', text: out.answer, out }])
    } catch (e) { setMsgs((m) => [...m, { role: 'ai', text: errMsg(e), err: true }]); toast(errMsg(e), 'error') } finally { setBusy(false) }
  }, [busy, shared, toast])

  useEffect(() => {
    const q = (loc.state as { ask?: string } | null)?.ask
    if (q && !asked.current) { asked.current = true; void ask(q) }
  }, [loc.state, ask])

  const e = shared.emotion
  return (
    <div className="container-x py-8 sm:py-12">
      <p className="eyebrow">NeuroGuide</p>
      <h1 className="h-display mt-2 text-4xl sm:text-5xl">Ask the science <span className="italic">behind the sound.</span></h1>
      <p className="mt-3 max-w-2xl text-espresso-700">A retrieval-augmented guide. Established science is kept apart from what the model inferred in your session.</p>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="card flex min-h-[520px] flex-col overflow-hidden">
          <div className="flex-1 space-y-4 overflow-auto p-4 sm:p-6" style={{ maxHeight: '65vh' }} aria-live="polite">
            {msgs.length === 0 && (
              <div className="grid place-items-center py-10 text-center"><LogoMark size={56} /><p className="mt-4 font-display text-2xl">How can I help you understand your session?</p>
                <div className="mt-5 flex max-w-xl flex-wrap justify-center gap-2">{sugg.map((s) => <button key={s} onClick={() => void ask(s)} className="chip transition hover:bg-sand-200">{s}</button>)}</div></div>
            )}
            {msgs.map((m, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={m.role === 'user' ? 'flex justify-end' : 'flex'}>
                <div className={`max-w-[92%] rounded-2xl px-4 py-3 ${m.role === 'user' ? 'bg-espresso-950 text-sand-50' : 'border border-sand-200 bg-white'} ${m.err ? '!border-espresso-700' : ''}`}>
                  {m.role === 'user' ? <p className="text-sm">{m.text}</p> : <Answer m={m} />}
                </div>
              </motion.div>
            ))}
            {busy && <div className="flex gap-1 px-2" role="status" aria-label="NeuroGuide is thinking">{[0, 1, 2].map((i) => <span key={i} className="h-2 w-2 rounded-full bg-espresso-600 pulse-soft" style={{ animationDelay: `${i * 0.2}s` }} />)}</div>}
            <div ref={end} />
          </div>
          {msgs.length > 0 && <div className="flex gap-2 overflow-x-auto border-t border-sand-200 px-4 py-2 scroll-x">{sugg.slice(0, 4).map((s) => <button key={s} onClick={() => void ask(s)} className="chip shrink-0 hover:bg-sand-200">{s}</button>)}</div>}
          <form onSubmit={(ev) => { ev.preventDefault(); void ask(input) }} className="flex gap-2 border-t border-sand-200 p-3">
            <label className="sr-only" htmlFor="q">Your question</label>
            <input id="q" className="input" maxLength={1000} value={input} onChange={(ev) => setInput(ev.target.value)} placeholder="Ask about EEG, emotion models or your music…" />
            <button className="btn-primary" disabled={busy || !input.trim()} type="submit">Send</button>
          </form>
        </div>
        <aside className="space-y-4">
          <div className="card p-5">
            <p className="label-mono">Session context</p>
            {e ? (
              <div className="mt-2 text-sm"><p className="font-display text-xl">{e.label}</p><p className="text-espresso-700">{e.quadrant}</p>
                <p className="mt-2 font-mono text-xs text-espresso-600">V {Math.round(e.valence * 100)} · A {Math.round(e.arousal * 100)} · F {Math.round(e.focus * 100)} · S {Math.round(e.stress * 100)}</p>
                {shared.profile && <p className="mt-1 font-mono text-xs text-espresso-600">{shared.profile.bpm} BPM · {shared.profile.mode_name}</p>}
                <p className="mt-2 text-xs text-espresso-600">Sent with each question so answers can explain your session.</p></div>
            ) : <p className="mt-2 text-sm text-espresso-700">No live session yet. Open the Lab to attach your latest estimated state; general questions work without it.</p>}
          </div>
          <Disclaimer />
        </aside>
      </div>
    </div>
  )
}
