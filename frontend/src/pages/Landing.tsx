import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { api, type AnalysisOut, type Meta, type RecommendOut, type Scenario } from '../lib/api'
import { ema } from '../lib/util'
import { Accordion, Counter, Disclaimer, Reveal, SectionHead } from '../components/ui'
import { ArchitectureDiagram, BrainContour, HeadbandDiagram, Headphones, PipelineStrip } from '../components/Illustrations'
import { EegCanvas, HeroWave, InteractiveEeg, type EegFrame } from '../components/Canvases'
import { MoodCompass } from '../components/lab/MoodCompass'
import { Gauges, type Smooth } from '../components/lab/LiveLab'
import { Artwork } from '../components/Artwork'

function Hero() {
  const { scrollY } = useScroll()
  const y = useTransform(scrollY, [0, 700], [0, 80])
  return (
    <section className="relative overflow-hidden">
      <div className="container-x relative pb-10 pt-14 sm:pt-24">
        <Reveal><p className="eyebrow">NeuroSonic AI · Brainwave → Emotion → Music</p></Reveal>
        <Reveal delay={0.08}><h1 className="h-display mt-5 max-w-4xl text-5xl leading-[1.02] sm:text-7xl lg:text-[5.5rem]">Listen to what your <span className="px-1 italic">mind</span> is feeling.</h1></Reveal>
        <Reveal delay={0.16}><p className="mt-6 max-w-xl text-lg text-espresso-700">Transform brainwave patterns into personalized sound experiences.</p></Reveal>
        <Reveal delay={0.24}>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/lab" className="btn-primary !px-7 !py-3.5 text-base">Start Brainwave Session</Link>
            <Link to="/lab#demo" className="btn-ghost !px-7 !py-3.5 text-base">Explore Demo</Link>
          </div>
        </Reveal>
        <motion.div style={{ y }} className="-mx-5 my-6 h-52 sm:-mx-8 sm:h-72"><HeroWave className="h-full w-full" /></motion.div>
        <Reveal delay={0.3}><PipelineStrip /></Reveal>
      </div>
    </section>
  )
}

function InteractiveEegSection() {
  const [freq, setFreq] = useState(10)
  const [amp, setAmp] = useState(0.6)
  const band = freq < 4 ? 'Delta' : freq < 8 ? 'Theta' : freq < 13 ? 'Alpha' : freq < 30 ? 'Beta' : 'Gamma'
  const note: Record<string, string> = { Delta: 'deep rest and sleep', Theta: 'drowsiness, inward attention', Alpha: 'relaxed wakefulness', Beta: 'active thinking and alertness', Gamma: 'high-frequency integration' }
  return (
    <section className="container-x py-20" aria-labelledby="ieeg">
      <SectionHead eyebrow="Interactive EEG" title={<span id="ieeg">Feel how a rhythm <span className="italic">looks</span></span>} sub="Drag the sliders to shape a synthetic oscillation. This is an illustration, not a recording." />
      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="card p-4"><InteractiveEeg freq={freq} amp={amp} className="h-64 w-full" /></div>
        <div className="card space-y-5 p-6">
          <label className="block"><span className="label-mono">Frequency · {freq} Hz</span><input className="range mt-3" type="range" min={1} max={40} value={freq} onChange={(e) => setFreq(+e.target.value)} aria-valuetext={`${freq} hertz, ${band} band`} /></label>
          <label className="block"><span className="label-mono">Amplitude · {Math.round(amp * 100)}%</span><input className="range mt-3" type="range" min={10} max={100} value={amp * 100} onChange={(e) => setAmp(+e.target.value / 100)} /></label>
          <div className="rounded-xl bg-sand-100 p-4"><p className="font-display text-2xl">{band} band</p><p className="text-sm text-espresso-700">Often linked to {note[band]}.</p></div>
        </div>
      </div>
    </section>
  )
}

const HOW = [
  { t: 'Capture', d: 'A 4-channel headband (TP9, AF7, AF8, TP10) records scalp voltage at 256 Hz. A demo stream simulates it for you.', v: <HeadbandDiagram className="mx-auto w-48" /> },
  { t: 'Clean & transform', d: 'Windows of 4 seconds are filtered, quality-scored and moved to the frequency domain.', v: <BrainContour className="mx-auto w-64" /> },
  { t: 'Estimate emotion', d: 'Band power, ratios and frontal alpha asymmetry feed a model that estimates valence, arousal, calmness, focus and stress.', v: <MoodCompass className="mx-auto w-64" plan={{ mode: 'match', target_key: null, shift: 1, current: { valence: 0.4, arousal: 0.7 }, target: { valence: 0.7, arousal: 0.25 }, music: { valence: 0.52, arousal: 0.5 }, trajectory: [{ valence: 0.4, arousal: 0.7 }, { valence: 0.5, arousal: 0.52 }, { valence: 0.62, arousal: 0.38 }, { valence: 0.7, arousal: 0.25 }] }} /> },
  { t: 'Compose & explain', d: 'A planner turns the state into tempo, key, texture and a gradual playlist, then explains its reasoning.', v: <Headphones className="mx-auto w-52" /> },
]

function HowItWorks() {
  return (
    <section id="how" className="container-x py-20" aria-labelledby="hiw">
      <SectionHead eyebrow="How it works" title={<span id="hiw">Four steps from scalp to sound</span>} />
      <div className="grid gap-10 lg:grid-cols-[1fr_1fr]">
        <ol className="space-y-6">
          {HOW.map((s, i) => (
            <Reveal key={s.t}><li className="card card-lift flex gap-4 p-5"><span className="font-display text-4xl font-light text-clay">{i + 1}</span><div><h3 className="font-display text-xl">{s.t}</h3><p className="mt-1 text-sm text-espresso-700">{s.d}</p><div className="mt-4 lg:hidden">{s.v}</div></div></li></Reveal>
          ))}
        </ol>
        <div className="relative hidden lg:block"><div className="sticky top-28 space-y-6">
          <div className="card grid place-items-center p-8"><HeadbandDiagram className="w-52" /></div>
          <div className="card grid place-items-center p-6"><Headphones className="w-56" /></div>
        </div></div>
      </div>
    </section>
  )
}

function Bridge() {
  const items = [['Delta · Theta', 'Slow, restful activity; more drowsy or inward states.', 'Warm pads, slow tempo'], ['Alpha', 'Relaxed wakefulness; calm, low-effort attention.', 'Open harmony, soft pulse'], ['Beta · Gamma', 'Active, effortful or alert processing.', 'Rhythmic drive, brighter timbre']]
  return (
    <section className="dark-section bg-espresso-950 py-20 text-sand-100">
      <div className="container-x">
        <SectionHead dark eyebrow="From brainwave to sound" title="Patterns become musical parameters" sub="The mapping is a transparent, rule-guided design, not a claim that a band 'is' an emotion." />
        <div className="scroll-x -mx-5 flex snap-x gap-4 overflow-x-auto px-5 pb-3 sm:mx-0 sm:px-0" tabIndex={0} aria-label="Brainwave to sound mapping carousel">
          {items.map(([a, b, c]) => (
            <div key={a} className="min-w-[280px] flex-1 snap-start rounded-2xl border border-espresso-700 bg-espresso-900 p-6 transition hover:-translate-y-1">
              <p className="label-mono !text-clay">EEG</p><p className="font-display text-2xl text-sand-50">{a}</p><p className="mt-1 text-sm text-sand-300">{b}</p>
              <div aria-hidden className="my-4 font-mono text-clay">↓</div>
              <p className="label-mono !text-clay">Sound</p><p className="font-display text-xl text-sand-50">{c}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function LiveTeaser() {
  const [scenario, setScenario] = useState<Scenario>('auto')
  const [data, setData] = useState<AnalysisOut | null>(null)
  const [frame, setFrame] = useState<EegFrame | null>(null)
  const [sm, setSm] = useState<Smooth | null>(null)
  const [rec, setRec] = useState<RecommendOut | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const smr = useRef<Smooth | null>(null)
  const seq = useRef(0)
  const sectionRef = useRef<HTMLElement>(null)
  const [near, setNear] = useState(false)
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => setNear(e.isIntersecting), { rootMargin: '200px' })
    if (sectionRef.current) io.observe(sectionRef.current)
    return () => io.disconnect()
  }, [])
  useEffect(() => {
    if (!near) return
    let stop = false, t = 4, timer: ReturnType<typeof setTimeout>
    const ac = new AbortController()
    const loop = async () => {
      try {
        const d = await api.demoWindow(scenario, t, ac.signal); if (stop) return
        t += 1; smr.current = ema(smr.current, { valence: d.emotion.valence, arousal: d.emotion.arousal, calmness: d.emotion.calmness, focus: d.emotion.focus, stress: d.emotion.stress, confidence: d.emotion.confidence }, 0.3)
        seq.current++; setSm(smr.current); setData(d); setErr(null); setFrame({ channels: d.waveform.channels, fs: d.waveform.fs, pollMs: 1000, stepS: 1, seq: seq.current })
      } catch (e) { if (stop || (e as Error).name === 'AbortError') return; setErr((e as Error).message) }
      timer = setTimeout(loop, 1000)
    }
    void loop()
    return () => { stop = true; ac.abort(); clearTimeout(timer) }
  }, [scenario, near])
  const label = data?.emotion.label
  useEffect(() => {
    if (!data) return
    const e = data.emotion
    const h = setTimeout(() => { api.recommend({ emotion: { valence: e.valence, arousal: e.arousal, calmness: e.calmness, focus: e.focus, stress: e.stress }, mode: 'shift', target: 'calm', shift: 0.6 }).then(setRec).catch(() => undefined) }, 300)
    return () => clearTimeout(h)
  }, [label]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section id="demo" ref={sectionRef} className="container-x py-20" aria-labelledby="lt">
      <SectionHead eyebrow="Live demo" title={<span id="lt">A tiny lab, running right now</span>} sub="Real calls to the demo EEG endpoint and the music planner. Open the full Lab for everything else." />
      <div className="card p-5 sm:p-6">
        {err && !data ? <p role="alert" className="text-sm">The backend is not reachable ({err}). Start it to see the live demo.</p> : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {(['auto', 'calm', 'stressed', 'excited'] as Scenario[]).map((s) => <button key={s} onClick={() => { smr.current = null; setScenario(s) }} aria-pressed={scenario === s} className={`rounded-full border px-3.5 py-1 text-sm capitalize ${scenario === s ? 'border-espresso-950 bg-espresso-950 text-sand-50' : 'border-sand-300'}`}>{s}</button>)}
              <span className="ml-auto font-display text-xl" aria-live="polite">{data?.emotion.label ?? '…'}</span>
            </div>
            <div className="mt-3 h-44">{data && <EegCanvas frame={frame} order={data.channels} quality={data.quality.per_channel} className="h-full w-full" />}</div>
            <div className="mt-3"><Gauges s={sm} /></div>
            {rec && (
              <div className="mt-4 flex flex-wrap items-center gap-4 rounded-xl bg-sand-100 p-4">
                <Artwork seed={rec.tracks[0]?.id ?? 'x'} energy={rec.profile.energy} brightness={rec.profile.brightness} className="h-16 w-16" />
                <div className="min-w-0 flex-1"><p className="label-mono">Suggested sound (shift toward calm)</p><p className="font-display text-lg">{rec.tracks[0]?.title} · {rec.profile.bpm} BPM · {rec.profile.mode_name}</p><p className="text-xs text-espresso-600">{rec.profile.instrumentation.join(' · ')}</p></div>
                <Link to="/lab" className="btn-primary">Open full lab</Link>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}

function Emotion() {
  const dims = [['Valence', 'Negative ↔ positive feeling'], ['Arousal', 'Calm ↔ activated'], ['Calmness', 'Settled, relaxed state'], ['Focus', 'Attentional engagement'], ['Stress', 'Tension tendency']]
  return (
    <section className="container-x py-20" aria-labelledby="ei">
      <SectionHead eyebrow="Emotion intelligence" title={<span id="ei">Five dimensions, <span className="italic">one estimate</span></span>} sub="Instead of a handful of rigid labels, the model reports continuous dimensions plus a confidence and the features that drove it." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {dims.map(([a, b], i) => <Reveal key={a} delay={i * 0.05}><div className="card card-lift h-full p-5"><p className="font-mono text-xs text-clay">0{i + 1}</p><h3 className="mt-2 font-display text-xl">{a}</h3><p className="mt-1 text-sm text-espresso-700">{b}</p></div></Reveal>)}
      </div>
    </section>
  )
}

function Transformation() {
  const [v, setV] = useState(0.5)
  const lerp = (a: number, b: number) => a + (b - a) * v
  const plan = { mode: 'shift' as const, target_key: 'calm', shift: v, current: { valence: 0.3, arousal: 0.8 }, target: { valence: 0.7, arousal: 0.2 }, music: { valence: lerp(0.3, 0.7), arousal: lerp(0.8, 0.2) }, trajectory: [{ valence: 0.3, arousal: 0.8 }, { valence: 0.43, arousal: 0.6 }, { valence: 0.57, arousal: 0.4 }, { valence: 0.7, arousal: 0.2 }] }
  return (
    <section className="dark-section bg-espresso-900 py-20 text-sand-100">
      <div className="container-x grid items-center gap-10 lg:grid-cols-2">
        <div>
          <SectionHead dark eyebrow="Music transformation" title="Match your mood, or gently move it" sub="Based on the iso principle: start near the listener's state, then travel gradually toward the target. This diagram is illustrative; the real planner lives in the Lab." />
          <label className="block"><span className="label-mono !text-sand-300">Illustration · {Math.round(v * 100)}% of the way</span><input type="range" className="range mt-3" min={0} max={100} value={v * 100} onChange={(e) => setV(+e.target.value / 100)} aria-label="Illustrative shift amount" /></label>
          <div className="mt-4 flex justify-between font-display text-lg"><span>Stressed</span><span>Calm</span></div>
        </div>
        <div className="rounded-2xl bg-sand-50 p-4"><MoodCompass plan={plan} className="mx-auto w-full max-w-[420px]" /></div>
      </div>
    </section>
  )
}

function Metrics() {
  const [meta, setMeta] = useState<Meta | null>(null)
  useEffect(() => { api.meta().then(setMeta).catch(() => undefined) }, [])
  const c = meta?.counts
  const items: [string, number | undefined, string][] = [['EEG frequency bands', c?.bands, 'delta to gamma'], ['EEG channels', c?.channels, 'TP9 AF7 AF8 TP10'], ['Mood dimensions', c?.dimensions, 'estimated per window'], ['Catalog presets', c?.presets, 'music building blocks'], ['API endpoints', c?.endpoints && c.endpoints > 0 ? c.endpoints : undefined, 'documented FastAPI routes']]
  return (
    <section className="container-x py-20" aria-labelledby="pm">
      <SectionHead eyebrow="Project metrics" title={<span id="pm">Facts, not claims</span>} sub="Counts reported live by the backend. No accuracy figures are shown because the bundled model is a synthetic-data baseline." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {items.map(([k, n, s]) => <div key={k} className="card p-5"><p className="font-display text-5xl font-light">{n != null ? <Counter to={n} /> : '—'}</p><p className="mt-2 text-sm font-medium">{k}</p><p className="text-xs text-espresso-600">{s}</p></div>)}
      </div>
    </section>
  )
}

const ROAD = [['Now', 'Demo EEG stream, upload analysis, emotion estimate, music planner & synth'], ['Next', 'Real-device streaming (e.g. via LSL) and per-user calibration'], ['Then', 'Trained models on real labelled data with proper validation'], ['Later', 'Richer generative audio providers and long-term listening feedback loops']]

export default function Landing() {
  return (
    <div>
      <Hero />
      <InteractiveEegSection />
      <Bridge />
      <HowItWorks />
      <LiveTeaser />
      <Emotion />
      <Transformation />

      <section className="container-x py-20" aria-labelledby="arch">
        <div className="dark-section rounded-3xl bg-espresso-950 p-6 sm:p-10">
          <SectionHead dark eyebrow="Architecture" title={<span id="arch">AI + neuroscience, end to end</span>} />
          <ArchitectureDiagram />
        </div>
      </section>

      <section className="container-x grid gap-8 py-10 lg:grid-cols-2">
        <div><SectionHead eyebrow="RAG · NeuroGuide" title="Answers with citations" sub="NeuroGuide retrieves passages from a curated knowledge base and separates established science from what the model inferred in your session." />
          <Link to="/guide" className="btn-ghost">Talk to NeuroGuide</Link></div>
        <div><SectionHead eyebrow="Explainable AI" title="Why this music?" sub="Every recommendation carries a step chain, feature attributions, fusion weights and caveats." />
          <Link to="/lab#explain" className="btn-ghost">See an explanation</Link></div>
      </section>

      <section className="container-x py-16" aria-labelledby="rf">
        <SectionHead eyebrow="Research foundation" title={<span id="rf">Grounded in established ideas</span>} sub="NeuroSonic is inspired by these concept areas. It does not replicate or validate any single study." />
        <Accordion items={[
          { q: 'Frontal alpha asymmetry', a: 'A line of research relates the balance of alpha power between right and left frontal electrodes to approach/withdrawal motivation. Findings are mixed, so it is used here as one feature among many.' },
          { q: 'Circumplex model of affect', a: 'Emotions can be placed on two axes, valence and arousal. The Mood Compass uses this plane to show where you are and where the music is heading.' },
          { q: 'Iso principle', a: 'In music therapy practice, listening begins close to the listener’s current mood and moves step by step toward a desired one. The transition playlist follows this idea.' },
          { q: 'DEAP-style datasets', a: 'Public datasets such as DEAP pair EEG with self-reported valence and arousal and are a common benchmark in the field. This prototype’s bundled model is trained on synthetic data and is not validated on DEAP.' },
        ]} />
      </section>

      <section className="container-x py-12" aria-labelledby="ts">
        <SectionHead eyebrow="Technology stack" title={<span id="ts">Built with</span>} />
        <div className="flex flex-wrap gap-2">{['React', 'TypeScript', 'Vite', 'Tailwind', 'Framer Motion', 'Recharts', 'FastAPI', 'Python', 'NumPy / SciPy', 'scikit-learn', 'SQLAlchemy', 'Web Audio API', 'Docker', 'nginx'].map((t) => <span key={t} className="chip !px-4 !py-1.5 text-sm">{t}</span>)}</div>
      </section>

      <Metrics />

      <section className="container-x pb-6" aria-labelledby="rm">
        <SectionHead eyebrow="Roadmap" title={<span id="rm">Where it goes next</span>} />
        <ol className="relative grid gap-4 border-l border-sand-300 pl-6 sm:grid-cols-2 sm:border-l-0 sm:pl-0 lg:grid-cols-4">
          {ROAD.map(([a, b]) => <li key={a} className="card card-lift p-5"><p className="label-mono !text-clay">{a}</p><p className="mt-2 text-sm text-espresso-800">{b}</p></li>)}
        </ol>
      </section>

      <section className="container-x py-16">
        <div className="dark-section relative overflow-hidden rounded-3xl bg-espresso-950 p-8 text-center sm:p-14">
          <h2 className="h-display !text-sand-50 text-3xl sm:text-5xl">Ready to hear your own signal?</h2>
          <p className="mx-auto mt-3 max-w-md text-sand-300">No sign-up needed. A guest session starts automatically.</p>
          <div className="mt-7 flex justify-center gap-3"><Link to="/lab" className="btn-light">Start Brainwave Session</Link><Link to="/login" className="btn-outline-light">Create account</Link></div>
        </div>
        <Disclaimer className="mt-6" />
      </section>
    </div>
  )
}
