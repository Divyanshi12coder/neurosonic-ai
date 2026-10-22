import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, errMsg, type AnalysisOut, type GenerateIn, type Mode, type MoodPoint, type Preset, type RecommendOut, type Scenario, type Target, type TargetInfo, type TrackOut } from '../lib/api'
import { DIMS } from '../lib/api'
import { downloadText, ema, sampleCsv } from '../lib/util'
import { useApp } from '../store/app'
import { Bar, Disclaimer, ErrorState, SectionHead } from '../components/ui'
import { HeadbandDiagram } from '../components/Illustrations'
import type { EegFrame } from '../components/Canvases'
import { Gauges, LiveLab, type Smooth } from '../components/lab/LiveLab'
import { MoodCompass } from '../components/lab/MoodCompass'
import { MoodSlider } from '../components/lab/MoodSlider'
import { MusicStudio } from '../components/lab/MusicStudio'
import { Explain } from '../components/lab/Explain'

const SCENARIOS: Scenario[] = ['auto', 'calm', 'focused', 'stressed', 'excited', 'drowsy', 'melancholic']
const TARGETS: Target[] = ['calm', 'focus', 'energize', 'refresh']
const CH = ['TP9', 'AF7', 'AF8', 'TP10']

interface Parsed { samples: Record<string, number[]>; fs: number }
function parseEeg(text: string, name: string, fsOverride?: number): Parsed {
  if (name.toLowerCase().endsWith('.json') || text.trim().startsWith('{')) {
    const j = JSON.parse(text)
    const samples = (j.samples ?? j.channels ?? j) as Record<string, number[]>
    const out: Record<string, number[]> = {}
    for (const c of CH) if (Array.isArray(samples[c])) out[c] = samples[c]
    if (!Object.keys(out).length) throw new Error('JSON needs {"fs":256,"samples":{"TP9":[..],"AF7":[..],"AF8":[..],"TP10":[..]}}')
    return { samples: out, fs: fsOverride ?? Number(j.fs ?? 256) }
  }
  const lines = text.trim().split(/\r?\n/)
  const head = lines[0].split(',').map((s) => s.trim())
  const idx = CH.map((c) => head.findIndex((h) => h.toLowerCase() === c.toLowerCase()))
  if (idx.some((i) => i < 0)) throw new Error('CSV header must include TP9, AF7, AF8, TP10 (optional time column)')
  const out: Record<string, number[]> = { TP9: [], AF7: [], AF8: [], TP10: [] }
  const ti = head.findIndex((h) => h.toLowerCase() === 'time')
  let t0 = NaN, t1 = NaN
  for (let i = 1; i < lines.length; i++) {
    const p = lines[i].split(',')
    CH.forEach((c, k) => out[c].push(Number(p[idx[k]])))
    if (ti >= 0) { const t = Number(p[ti]); if (i === 1) t0 = t; t1 = t }
  }
  const est = ti >= 0 && out.TP9.length > 1 ? Math.round((out.TP9.length - 1) / (t1 - t0)) : 256
  return { samples: out, fs: fsOverride ?? (est > 0 ? est : 256) }
}

export default function Lab() {
  const { user, toast, setShared } = useApp()
  const nav = useNavigate()
  const loc = useLocation()
  const [source, setSource] = useState<'demo' | 'upload'>('demo')
  const [scenario, setScenario] = useState<Scenario>('auto')
  const [running, setRunning] = useState(true)
  const [data, setData] = useState<AnalysisOut | null>(null)
  const [frame, setFrame] = useState<EegFrame | null>(null)
  const [smooth, setSmooth] = useState<Smooth | null>(null)
  const [rel, setRel] = useState<Record<string, number> | null>(null)
  const [pollErr, setPollErr] = useState<string | null>(null)
  const smRef = useRef<Smooth | null>(null)
  const relRef = useRef<Record<string, number> | null>(null)
  const seq = useRef(0)

  // upload
  const [uploadWin, setUploadWin] = useState<AnalysisOut[] | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadInfo, setUploadInfo] = useState<string | null>(null)

  // recommendation state
  const [mode, setMode] = useState<Mode>('shift')
  const [target, setTarget] = useState<Target>('calm')
  const [shift, setShift] = useState(0.6)
  const [textDraft, setTextDraft] = useState('')
  const [text, setText] = useState('')
  const [rec, setRec] = useState<RecommendOut | null>(null)
  const [recErr, setRecErr] = useState<string | null>(null)
  const [recBusy, setRecBusy] = useState(false)
  const [targets, setTargets] = useState<Record<string, TargetInfo> | null>(null)
  const [snap, setSnap] = useState<MoodPoint | null>(null)

  // music
  const [track, setTrack] = useState<TrackOut | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genErr, setGenErr] = useState<string | null>(null)
  const [variation, setVariation] = useState(0)
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const [rating, setRating] = useState(0)

  useEffect(() => { api.targets().then(setTargets).catch(() => undefined) }, [])
  useEffect(() => { if (loc.hash) setTimeout(() => document.getElementById(loc.hash.slice(1))?.scrollIntoView({ behavior: 'smooth' }), 400) }, [loc.hash])

  const ingest = useCallback((d: AnalysisOut, step: number) => {
    const e = d.emotion
    const next = { valence: e.valence, arousal: e.arousal, calmness: e.calmness, focus: e.focus, stress: e.stress, confidence: e.confidence }
    smRef.current = ema(smRef.current, next, 0.3)
    relRef.current = ema(relRef.current, d.features.relative_band_power, 0.4)
    setSmooth(smRef.current); setRel(relRef.current); setData(d); setPollErr(null)
    seq.current += 1
    setFrame({ channels: d.waveform.channels, fs: d.waveform.fs, pollMs: 1000, stepS: step, seq: seq.current })
  }, [])

  // demo polling
  useEffect(() => {
    if (source !== 'demo' || !running) return
    let stop = false
    let t = 4
    const ac = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const loop = async () => {
      const t0 = performance.now()
      try { const d = await api.demoWindow(scenario, t, ac.signal); if (stop) return; ingest(d, 1); t += 1 }
      catch (e) { if (stop || (e as Error).name === 'AbortError') return; setPollErr(errMsg(e)) }
      timer = setTimeout(loop, Math.max(200, 1000 - (performance.now() - t0)))
    }
    void loop()
    return () => { stop = true; ac.abort(); clearTimeout(timer) }
  }, [source, scenario, running, ingest])

  // upload replay
  useEffect(() => {
    if (source !== 'upload' || !running || !uploadWin?.length) return
    let i = 0
    const id = setInterval(() => { ingest(uploadWin[i % uploadWin.length], 1); i++ }, 1000)
    ingest(uploadWin[0], 1); i = 1
    return () => clearInterval(id)
  }, [source, running, uploadWin, ingest])

  const onFile = async (f: File) => {
    setUploading(true); setUploadInfo(null)
    try {
      const txt = await f.text()
      const parsed = parseEeg(txt, f.name)
      const n = parsed.samples.TP9?.length ?? 0
      const win = Math.round(parsed.fs * 4)
      if (n < win) throw new Error(`Need at least 4 seconds of data (${win} samples at ${parsed.fs} Hz); got ${n}.`)
      const s = await api.upload(f, parsed.fs, f.name.replace(/\.[^.]+$/, '')).catch((e) => { toast(`Session not stored: ${errMsg(e)}`, 'error'); return null })
      const out: AnalysisOut[] = []
      const maxWin = 24
      for (let st = 0, k = 0; st + win <= n && k < maxWin; st += parsed.fs, k++) {
        const sl: Record<string, number[]> = {}
        for (const c of Object.keys(parsed.samples)) sl[c] = parsed.samples[c].slice(st, st + win)
        out.push(await api.analyze({ samples: sl, fs: parsed.fs }))
      }
      smRef.current = null
      setUploadWin(out); setSource('upload'); setRunning(true)
      setUploadInfo(`${f.name}: ${out.length} analysed windows at ${parsed.fs} Hz${s ? ` · stored as session #${s.id}` : ''}. Replaying in a loop.`)
      toast('Upload analysed', 'success')
    } catch (e) { toast(errMsg(e), 'error'); setUploadInfo(errMsg(e)) } finally { setUploading(false) }
  }

  // refresh the "current state" snapshot used for recommendations every ~6s (keeps music stable)
  const hasSm = !!smooth
  useEffect(() => {
    if (!hasSm) return
    const upd = () => { const s = smRef.current; if (s) setSnap({ valence: s.valence, arousal: s.arousal, calmness: s.calmness, focus: s.focus, stress: s.stress, confidence: s.confidence }) }
    upd()
    const id = setInterval(upd, 6000)
    return () => clearInterval(id)
  }, [hasSm])

  const body = useMemo<GenerateIn>(() => ({
    emotion: snap, mode, target: mode === 'shift' ? target : null, shift: mode === 'shift' ? shift : 1,
    text: text || null, quality: data?.quality.label ?? null,
    feature_importance: data?.emotion.feature_importance ?? null,
  }), [snap, mode, target, shift, text, data?.quality.label, data?.emotion.feature_importance])
  const bodyRef = useRef(body); bodyRef.current = body

  // debounced recommend
  const sig = `${snap?.valence}|${snap?.arousal}|${mode}|${target}|${shift}|${text}`
  useEffect(() => {
    if (!snap && !text) return
    const ac = new AbortController()
    const h = setTimeout(async () => {
      setRecBusy(true)
      try { const r = await api.recommend({ ...bodyRef.current, feature_importance: bodyRef.current.feature_importance?.slice(0, 12) }, ac.signal); setRec(r); setRecErr(null) }
      catch (e) { if ((e as Error).name !== 'AbortError') setRecErr(errMsg(e)) }
      finally { if (!ac.signal.aborted) setRecBusy(false) }
    }, 250)
    return () => { clearTimeout(h); ac.abort() }
  }, [sig]) // eslint-disable-line react-hooks/exhaustive-deps

  // share context with NeuroGuide
  useEffect(() => {
    if (data) setShared({ emotion: { ...data.emotion, ...(smRef.current ?? {}) } as never, profile: rec?.profile ?? null, scenario: data.scenario })
  }, [data?.emotion.label, rec?.profile, setShared]) // eslint-disable-line react-hooks/exhaustive-deps

  const generate = async (opts: { preset?: Preset; variation?: number } = {}) => {
    setGenerating(true); setGenErr(null); setRating(0)
    try {
      const out = await api.generate({ ...bodyRef.current, feature_importance: bodyRef.current.feature_importance?.slice(0, 12), preset_id: opts.preset?.id ?? null, variation: opts.variation ?? variation, duration_s: 24 })
      setTrack(out.track); setRec(out.recommendation); setActivePreset(out.track.preset_id)
      if (out.provider_note) toast(out.provider_note)
    } catch (e) { setGenErr(errMsg(e)) } finally { setGenerating(false) }
  }
  const regenerate = () => { const v = variation + 1; setVariation(v); void generate({ variation: v }) }
  const save = async () => {
    if (!track?.id) return
    try { await api.saveTrack(track.id, !track.saved); setTrack({ ...track, saved: !track.saved }); toast(track.saved ? 'Removed from favorites' : 'Saved to favorites', 'success') } catch (e) { toast(errMsg(e), 'error') }
  }
  const rate = async (n: number) => {
    if (!track?.id) return
    setRating(n)
    try { await api.feedback({ track_id: track.id, rating: n, mood_after: snap ? { valence: smRef.current?.valence ?? snap.valence, arousal: smRef.current?.arousal ?? snap.arousal } : null }); toast('Thanks, feedback recorded', 'success') } catch (e) { toast(errMsg(e), 'error') }
  }

  const tInfo = targets?.[target]
  const curLabel = data?.emotion.label ?? 'Current state'
  const rightLabel = mode === 'match' ? 'Match' : tInfo?.label ?? target
  const backendDown = pollErr && !data

  return (
    <div>
      <section className="container-x pb-6 pt-8 sm:pt-12">
        <p className="eyebrow">Brainwave lab</p>
        <h1 className="h-display mt-2 text-4xl sm:text-5xl">Read the signal. <span className="italic">Shape the sound.</span></h1>
        <p className="mt-3 max-w-2xl text-espresso-700">Every number on this page comes from the NeuroSonic API: EEG window analysis, the emotion model and the music planner.</p>
      </section>

      {backendDown && <div className="container-x py-6"><ErrorState title="Backend unreachable" message={`${pollErr} The UI proxies /api to the FastAPI server (default http://localhost:8000).`} onRetry={() => { setRunning(false); setTimeout(() => setRunning(true), 50) }} /></div>}

      {/* Session controls */}
      <section id="demo" aria-labelledby="sc" className="container-x py-4">
        <div className="card grid gap-6 p-5 sm:p-6 lg:grid-cols-[1fr_200px]">
          <div>
            <h2 id="sc" className="font-display text-xl">Session</h2>
            <div className="mt-3 inline-flex rounded-full border border-sand-300 bg-sand-100 p-1" role="tablist" aria-label="EEG source">
              {(['demo', 'upload'] as const).map((s) => (
                <button key={s} role="tab" aria-selected={source === s} onClick={() => { setSource(s); smRef.current = null }}
                  className={`rounded-full px-4 py-1.5 text-sm transition ${source === s ? 'bg-espresso-950 text-sand-50' : 'text-espresso-800'}`}>{s === 'demo' ? 'Demo EEG stream' : 'Upload EEG'}</button>
              ))}
            </div>
            {source === 'demo' ? (
              <div className="mt-4">
                <p className="label-mono mb-2">Scenario {scenario === 'auto' && data?.scenario ? <span className="normal-case tracking-normal text-espresso-700">· now: {data.scenario}</span> : null}</p>
                <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Scenario">
                  {SCENARIOS.map((s) => (
                    <button key={s} role="radio" aria-checked={scenario === s} onClick={() => { setScenario(s); smRef.current = null }}
                      className={`rounded-full border px-3.5 py-1.5 text-sm capitalize transition ${scenario === s ? 'border-espresso-950 bg-espresso-950 text-sand-50' : 'border-sand-300 bg-white hover:bg-sand-100'}`}>{s}</button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <label className="flex cursor-pointer flex-col items-center rounded-2xl border border-dashed border-sand-300 bg-sand-50 p-6 text-center hover:bg-sand-100 focus-within:ring-2 focus-within:ring-espresso-700">
                  <span className="font-display text-lg">{uploading ? 'Analysing…' : 'Choose a CSV or JSON EEG file'}</span>
                  <span className="mt-1 text-xs text-espresso-600">Max a few minutes of data; at least 4 seconds.</span>
                  <input type="file" accept=".csv,.json,text/csv,application/json" className="sr-only" disabled={uploading} onChange={(e) => { const f = e.target.files?.[0]; if (f) void onFile(f); e.target.value = '' }} />
                </label>
                {uploadInfo && <p role="status" className="text-sm text-espresso-700">{uploadInfo}</p>}
                <details className="rounded-xl border border-sand-200 bg-white p-3 text-sm">
                  <summary className="cursor-pointer font-medium">Format help</summary>
                  <p className="mt-2 text-espresso-700">CSV with header <code className="font-mono text-xs">time,TP9,AF7,AF8,TP10</code>, microvolts, one row per sample (sampling rate is inferred from <code className="font-mono text-xs">time</code>, else 256 Hz). JSON: <code className="font-mono text-xs">{'{"fs":256,"samples":{"TP9":[...],"AF7":[...],"AF8":[...],"TP10":[...]}}'}</code></p>
                  <button className="btn-ghost mt-3 !py-1.5" onClick={() => downloadText('neurosonic-sample.csv', sampleCsv())}>Download sample CSV</button>
                </details>
              </div>
            )}
            <div className="mt-5 flex items-center gap-3">
              <button className="btn-primary" onClick={() => setRunning(!running)} aria-pressed={running}>{running ? '❚❚ Pause stream' : '▶ Resume stream'}</button>
              <span className="font-mono text-xs text-espresso-600"><span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${running && data ? 'bg-clay pulse-soft' : 'bg-sand-300'}`} />{running ? (data ? 'streaming' : 'connecting…') : 'paused'}</span>
            </div>
          </div>
          <div className="hidden lg:block"><HeadbandDiagram className="mx-auto w-44" quality={data?.quality.per_channel} /></div>
        </div>
      </section>

      {/* Live lab */}
      <section id="live" aria-labelledby="ll" className="container-x py-6">
        <h2 id="ll" className="mb-4 font-display text-2xl">Live EEG lab</h2>
        <LiveLab data={data} smooth={smooth} frame={frame} rel={rel} />
        <div className="mt-5"><Gauges s={smooth} /></div>
        {data?.quality && data.quality.overall < 0.5 && <p role="alert" className="mt-3 rounded-xl border border-sand-300 bg-sand-100 p-3 text-sm">Signal quality is low; estimates are less reliable.</p>}
      </section>

      {/* Compass + slider */}
      <section id="compass" aria-labelledby="mc" className="container-x py-10">
        <SectionHead eyebrow="Mood compass" title={<span id="mc">Where you are, where music can take you</span>} />
        <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.1fr]">
          <div className="card p-4"><MoodCompass plan={rec?.plan} className="mx-auto w-full max-w-[460px]" />
            <ul className="mt-2 flex flex-wrap justify-center gap-4 font-mono text-[11px] text-espresso-700">
              <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-espresso-950" />Now</li><li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border-2 border-espresso-950" />Target</li><li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-clay" />Music</li><li>- - Stages</li>
            </ul>
          </div>
          <div className="space-y-5">
            <div className="card p-5 sm:p-6">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-display text-xl">Mood transformation</h3>
                <div className="inline-flex rounded-full border border-sand-300 bg-sand-100 p-1" role="radiogroup" aria-label="Mode">
                  {(['match', 'shift'] as Mode[]).map((m) => <button key={m} role="radio" aria-checked={mode === m} onClick={() => setMode(m)} className={`rounded-full px-3 py-1 font-mono text-[11px] uppercase tracking-wider ${mode === m ? 'bg-espresso-950 text-sand-50' : 'text-espresso-800'}`}>{m === 'match' ? 'Match my mood' : 'Shift my mood'}</button>)}
                </div>
              </div>
              <MoodSlider value={mode === 'match' ? 0 : shift} onChange={(v) => { setMode('shift'); setShift(v) }} left={curLabel.toUpperCase()} right={rightLabel.toUpperCase()} />
              <div className="mt-5 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Target mood">
                <button role="radio" aria-checked={mode === 'match'} onClick={() => setMode('match')} className={`rounded-full border px-4 py-1.5 font-mono text-xs uppercase tracking-wider ${mode === 'match' ? 'border-espresso-950 bg-espresso-950 text-sand-50' : 'border-sand-300 bg-white hover:bg-sand-100'}`}>Match</button>
                {TARGETS.map((t) => <button key={t} role="radio" aria-checked={mode === 'shift' && target === t} title={targets?.[t]?.blurb} onClick={() => { setTarget(t); setMode('shift') }} className={`rounded-full border px-4 py-1.5 font-mono text-xs uppercase tracking-wider ${mode === 'shift' && target === t ? 'border-espresso-950 bg-espresso-950 text-sand-50' : 'border-sand-300 bg-white hover:bg-sand-100'}`}>{t}</button>)}
              </div>
              {mode === 'shift' && tInfo && <p className="mt-3 text-sm text-espresso-700"><span className="font-medium">{tInfo.label}:</span> {tInfo.blurb}</p>}
            </div>
            <div className="card p-5" aria-live="polite">
              <div className="mb-3 flex items-center justify-between"><h3 className="font-display text-xl">Music profile</h3>{recBusy && <span className="font-mono text-[11px] text-espresso-600 pulse-soft">updating…</span>}</div>
              {recErr && <p role="alert" className="mb-3 text-sm text-espresso-800">{recErr}</p>}
              {rec ? (
                <>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    {[['BPM', String(rec.profile.bpm)], ['Key / scale', rec.profile.mode_name], ['Texture', rec.profile.texture]].map(([k, v]) => (
                      <div key={k} className="rounded-xl bg-sand-100 px-2 py-3"><p className="label-mono !text-[10px]">{k}</p><motion.p key={v} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="mt-1 font-display text-lg">{v}</motion.p></div>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">{rec.profile.instrumentation.map((i) => <span key={i} className="chip">{i}</span>)}<span className="chip font-mono">{rec.profile.genre}</span><span className="chip">{rec.profile.percussion}</span></div>
                  <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-2.5">
                    {['valence', 'arousal', 'energy', 'brightness', 'calmness', 'intensity'].map((k) => <Bar key={k} label={k} value={rec.profile.mood_vector?.[k] ?? 0} right={`${Math.round((rec.profile.mood_vector?.[k] ?? 0) * 100)}`} />)}
                  </div>
                </>
              ) : <p className="text-sm text-espresso-600">Waiting for the first EEG window to plan the music…</p>}
            </div>
          </div>
        </div>

        {/* Text */}
        <div className="card mt-6 p-5 sm:p-6">
          <form onSubmit={(e) => { e.preventDefault(); setText(textDraft.trim()) }} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex-1"><span className="label-mono">Describe how you feel (optional)</span>
              <input className="input mt-1.5" maxLength={500} value={textDraft} onChange={(e) => setTextDraft(e.target.value)} placeholder="I feel mentally exhausted but I want to focus" />
            </label>
            <button className="btn-primary" type="submit">Fuse with EEG</button>
            {text && <button type="button" className="btn-ghost" onClick={() => { setText(''); setTextDraft('') }}>Clear</button>}
          </form>
          {rec?.nlp && text && (
            <div className="mt-4 grid gap-4 border-t border-sand-200 pt-4 sm:grid-cols-3">
              <div><p className="label-mono">Parsed ({rec.nlp.provider})</p><div className="mt-2 flex flex-wrap gap-1.5">{rec.nlp.emotions.map((e) => <span key={e} className="chip">{e}</span>)}{rec.nlp.intent && <span className="chip font-mono">intent: {rec.nlp.intent}</span>}</div>
                {rec.nlp.desired_transition && <p className="mt-2 text-sm text-espresso-700">{Object.entries(rec.nlp.desired_transition).map(([k, v]) => `${k} ${v}`).join(' → ')}</p>}
                {[...rec.nlp.music_preferences, ...rec.nlp.context].length > 0 && <p className="mt-2 text-xs text-espresso-600">{[...rec.nlp.music_preferences, ...rec.nlp.context].join(' · ')}</p>}</div>
              <div><p className="label-mono">Fusion weights</p><div className="mt-2 space-y-2">{Object.entries(rec.fusion_weights).map(([k, v]) => <Bar key={k} label={k} value={v} right={`${Math.round(v * 100)}%`} tone="clay" />)}</div></div>
              <div><p className="label-mono">Fused state</p><div className="mt-2 space-y-2">{DIMS.map((k) => <Bar key={k} label={k} value={rec.fused_state[k] ?? 0} right={`${Math.round((rec.fused_state[k] ?? 0) * 100)}`} />)}</div></div>
            </div>
          )}
        </div>
      </section>

      {/* Studio */}
      <section id="studio" aria-labelledby="ms" className="container-x py-10">
        <SectionHead eyebrow="Music studio" title={<span id="ms">Turn the plan into sound</span>} sub="Audio is rendered by the backend from the plan above. Generation can take a few seconds." />
        <MusicStudio track={track} generating={generating} error={genErr} rec={rec} authed={!!user} rating={rating} variation={variation} activePreset={activePreset}
          onGenerate={() => void generate()} onRegenerate={regenerate} onPreset={(p) => void generate({ preset: p })} onSave={() => void save()} onRate={(n) => void rate(n)} />
      </section>

      {/* Explain */}
      <section id="explain" aria-labelledby="mx" className="dark-section-lite container-x py-10">
        <SectionHead eyebrow="Explainable AI" title={<span id="mx">Why this music?</span>} sub="Each recommendation ships with its reasoning, attributions and caveats." />
        <Explain rec={rec} />
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button className="btn-primary" onClick={() => nav('/guide', { state: { ask: 'Why did you recommend this type of music?' } })}>✦ Ask NeuroGuide about this session</button>
          <Link to="/history" className="btn-ghost">View history</Link>
        </div>
        <Disclaimer className="mt-6" />
      </section>
    </div>
  )
}
