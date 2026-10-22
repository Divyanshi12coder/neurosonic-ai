import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import type { Preset, RecommendOut, TrackOut } from '../../lib/api'
import { Artwork, artFor } from '../Artwork'
import { Empty } from '../ui'

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

function useWavePeaks(url: string | undefined, n = 180) {
  const [peaks, setPeaks] = useState<number[] | null>(null)
  useEffect(() => {
    setPeaks(null)
    if (!url) return
    const ac = new AbortController()
    let ctx: AudioContext | null = null
    ;(async () => {
      try {
        const buf = await (await fetch(url, { signal: ac.signal })).arrayBuffer()
        const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
        ctx = new AC()
        const audio = await ctx.decodeAudioData(buf)
        const d = audio.getChannelData(0), step = Math.floor(d.length / n) || 1
        const out: number[] = []
        for (let i = 0; i < n; i++) { let m = 0; for (let j = i * step; j < (i + 1) * step && j < d.length; j += 8) m = Math.max(m, Math.abs(d[j])); out.push(m) }
        const mx = Math.max(...out, 1e-6)
        setPeaks(out.map((p) => p / mx))
      } catch { /* aborted or undecodable — fall back to bar-less track */ } finally { void ctx?.close() }
    })()
    return () => ac.abort()
  }, [url, n])
  return peaks
}

function Waveform({ peaks, progress, onSeek }: { peaks: number[] | null; progress: number; onSeek: (p: number) => void }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const cv = ref.current; if (!cv) return
    const draw = () => {
      const r = cv.getBoundingClientRect(); const dpr = Math.min(window.devicePixelRatio || 1, 2)
      cv.width = r.width * dpr; cv.height = r.height * dpr
      const c = cv.getContext('2d'); if (!c) return
      c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, r.width, r.height)
      const n = peaks?.length ?? 90, bw = r.width / n
      for (let i = 0; i < n; i++) {
        const p = peaks ? peaks[i] : 0.15 + 0.1 * Math.sin(i * 0.5)
        const h = Math.max(3, p * r.height * 0.92)
        c.fillStyle = i / n <= progress ? '#2B1B16' : '#CBB9AC'
        c.beginPath(); c.roundRect(i * bw + bw * 0.18, (r.height - h) / 2, bw * 0.64, h, 2); c.fill()
      }
    }
    draw()
    const ro = new ResizeObserver(draw); ro.observe(cv)
    return () => ro.disconnect()
  }, [peaks, progress])
  return (
    <canvas ref={ref} className="h-16 w-full cursor-pointer" role="presentation"
      onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); onSeek((e.clientX - r.left) / r.width) }} />
  )
}

export function MusicStudio({ track, generating, error, rec, onGenerate, onRegenerate, onPreset, onSave, onRate, rating, authed, activePreset, variation }: {
  track: TrackOut | null; generating: boolean; error: string | null; rec: RecommendOut | null
  onGenerate: () => void; onRegenerate: () => void; onPreset: (p: Preset) => void; onSave: () => void; onRate: (n: number) => void
  rating: number; authed: boolean; activePreset?: string | null; variation: number
}) {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [dur, setDur] = useState(0)
  const [vol, setVol] = useState(0.8)
  const peaks = useWavePeaks(track?.audio_url)

  useEffect(() => { setPlaying(false); setTime(0); setDur(track?.duration_s ?? 0) }, [track?.audio_id, track?.duration_s])
  useEffect(() => { if (audio.current) audio.current.volume = vol }, [vol])
  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => { if (audio.current) setTime(audio.current.currentTime); raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  const toggle = useCallback(() => {
    const a = audio.current; if (!a) return
    if (a.paused) void a.play().catch(() => setPlaying(false)); else a.pause()
  }, [])
  const seek = (p: number) => { const a = audio.current; if (a && dur) { a.currentTime = Math.max(0, Math.min(1, p)) * dur; setTime(a.currentTime) } }
  const prof = track?.profile

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
      <div className="card p-5 sm:p-6">
        <div className="flex flex-col gap-5 sm:flex-row">
          <div className="relative mx-auto aspect-square w-full max-w-[240px] shrink-0 overflow-hidden rounded-2xl shadow-lift sm:mx-0">
            {track ? <Artwork {...artFor(track)} className="h-full w-full" title={`Artwork for ${track.title}`} /> : <Artwork seed={7} className="h-full w-full opacity-60" title="Placeholder artwork" />}
            {generating && (
              <div className="absolute inset-0 grid place-items-center bg-espresso-950/70 text-sand-50" role="status">
                <div className="flex items-end gap-1" aria-hidden>{[0, 1, 2, 3, 4].map((i) => <span key={i} className="h-8 w-1.5 origin-bottom rounded bg-sand-100" style={{ animation: `eq .9s ${i * 0.12}s infinite ease-in-out` }} />)}</div>
                <p className="absolute bottom-4 font-mono text-xs">Composing…</p>
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="label-mono">{track ? `${prof?.genre ?? ''} · ${track.provider}` : 'Music Studio'}</p>
            <h3 className="mt-1 font-display text-3xl leading-tight">{track?.title ?? (generating ? 'Generating…' : 'Nothing generated yet')}</h3>
            <p className="text-sm text-espresso-700">{track?.subtitle ?? 'Generate a track tuned to your current mood plan.'}</p>
            {prof && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                <span className="chip font-mono">{prof.bpm} BPM</span><span className="chip font-mono">{prof.mode_name}</span><span className="chip">{prof.texture}</span>
                {prof.instrumentation.slice(0, 3).map((i) => <span key={i} className="chip">{i}</span>)}
              </div>
            )}
            <div className="mt-5 flex flex-wrap gap-2">
              <button className="btn-primary" onClick={onGenerate} disabled={generating}>{generating ? 'Generating…' : track ? 'Generate new' : 'Generate music'}</button>
              <button className="btn-ghost" onClick={onRegenerate} disabled={generating} title={`Take #${variation + 1}`}>↻ Regenerate</button>
              <button className="btn-ghost" onClick={onSave} disabled={!track || !authed || track.id == null} aria-pressed={!!track?.saved}>{track?.saved ? '♥ Saved' : '♡ Save'}</button>
            </div>
            {error && <p role="alert" className="mt-3 rounded-lg border border-sand-300 bg-sand-100 px-3 py-2 text-sm text-espresso-800">{error}</p>}
          </div>
        </div>

        <div className="mt-6">
          <Waveform peaks={track ? peaks : null} progress={dur ? time / dur : 0} onSeek={seek} />
          {track && (
            <>
              <audio ref={audio} src={track.audio_url} preload="auto" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => { setPlaying(false); setTime(0) }}
                onLoadedMetadata={(e) => setDur(e.currentTarget.duration || track.duration_s)} />
              <div className="mt-2 flex items-center gap-3">
                <button onClick={toggle} aria-label={playing ? 'Pause' : 'Play'} className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-espresso-950 text-sand-50 transition hover:bg-espresso-800 active:scale-95">
                  {playing ? <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="2" width="3.5" height="12" rx="1" /><rect x="9.5" y="2" width="3.5" height="12" rx="1" /></svg>
                    : <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l9-5.5z" /></svg>}
                </button>
                <span className="w-10 font-mono text-xs text-espresso-700">{mmss(time)}</span>
                <input type="range" className="range flex-1" min={0} max={1000} value={dur ? (time / dur) * 1000 : 0} onChange={(e) => seek(Number(e.target.value) / 1000)} aria-label="Seek" />
                <span className="w-10 text-right font-mono text-xs text-espresso-700">{mmss(dur)}</span>
                <label className="hidden items-center gap-2 sm:flex"><span className="sr-only">Volume</span>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#63463B" strokeWidth="1.8" strokeLinecap="round"><path d="M4 9v6h4l5 4V5L8 9zM16.5 8.5a5 5 0 010 7" /></svg>
                  <input type="range" className="range w-20" min={0} max={100} value={vol * 100} onChange={(e) => setVol(Number(e.target.value) / 100)} aria-label="Volume" />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-sand-200 pt-4">
                <span className="label-mono">Rate this track</span>
                <div role="radiogroup" aria-label="Rating" className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button key={n} role="radio" aria-checked={rating === n} aria-label={`${n} star${n > 1 ? 's' : ''}`} disabled={!authed || track.id == null} onClick={() => onRate(n)}
                      className="p-0.5 text-2xl leading-none text-sand-300 transition hover:scale-110 disabled:opacity-40" style={n <= rating ? { color: '#B08968' } : undefined}>★</button>
                  ))}
                </div>
                <span className="ml-auto font-mono text-[10px] text-espresso-600">{track.prompt.slice(0, 60)}…</span>
              </div>
            </>
          )}
          {!track && !generating && <Empty title="Press generate to compose">The audio is synthesised by the backend from your mood plan — tempo, key, texture and instrumentation come from the profile above.</Empty>}
        </div>
      </div>

      <div className="space-y-5">
        <div className="card p-5">
          <h3 className="font-display text-lg">Recommended presets</h3>
          <p className="text-xs text-espresso-600">Catalog matches for your plan. Click one to generate it.</p>
          <ul className="mt-3 max-h-[300px] space-y-1.5 overflow-auto pr-1 scroll-x">
            {(rec?.tracks ?? []).map((p) => (
              <li key={p.id}>
                <button onClick={() => onPreset(p)} disabled={generating} aria-pressed={activePreset === p.id}
                  className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition hover:bg-sand-100 disabled:opacity-60 ${activePreset === p.id ? 'border-espresso-700 bg-sand-100' : 'border-sand-200'}`}>
                  <Artwork seed={p.id} brightness={0.4 + p.point.valence * 0.4} energy={p.point.arousal} valence={p.point.valence} className="h-11 w-11 shrink-0" rounded />
                  <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{p.title}</span><span className="block truncate text-xs text-espresso-600">{p.genre} · {p.subtitle}</span></span>
                  <span className="font-mono text-xs text-espresso-700">{Math.round(p.fit * 100)}%</span>
                </button>
              </li>
            ))}
            {!rec && <li className="text-sm text-espresso-600">Waiting for a recommendation…</li>}
          </ul>
        </div>
        <div className="card p-5">
          <h3 className="font-display text-lg">Transition playlist <span className="text-sm font-light italic text-espresso-600">· iso principle</span></h3>
          <p className="text-xs text-espresso-600">Starts near your state, then moves gradually toward the target.</p>
          <ol className="mt-4 space-y-0">
            {(rec?.playlist ?? []).map((p, i, a) => (
              <li key={p.id + i} className="relative flex gap-3 pb-4 last:pb-0">
                {i < a.length - 1 && <span aria-hidden className="absolute left-[11px] top-6 h-full w-px bg-sand-300" />}
                <motion.span initial={{ scale: 0.6 }} animate={{ scale: 1 }} className="z-10 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-espresso-950 font-mono text-[10px] text-sand-50">{p.stage ?? i + 1}</motion.span>
                <button className="min-w-0 text-left" onClick={() => onPreset(p)} disabled={generating}>
                  <span className="block truncate text-sm font-medium hover:underline">{p.title}</span>
                  <span className="block truncate text-xs text-espresso-600">{p.genre} · {rec?.trajectory_profiles?.[i]?.bpm ?? ''} BPM</span>
                </button>
              </li>
            ))}
            {!rec && <li className="text-sm text-espresso-600">—</li>}
          </ol>
        </div>
      </div>
    </div>
  )
}
