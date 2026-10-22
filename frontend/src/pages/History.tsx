import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, Bar as RBar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { api, errMsg, type Analytics, type MoodLog, type SessionOut, type TrackOut } from '../lib/api'
import { useApp } from '../store/app'
import { timeAgo } from '../lib/util'
import { Artwork, artFor } from '../components/Artwork'
import { Empty, ErrorState, Skeleton } from '../components/ui'

const SERIES = [['valence', '#2B1B16'], ['arousal', '#B08968'], ['focus', '#63463B'], ['stress', '#CBB9AC']] as const
const axis = { fontSize: 10, fill: '#80665A', fontFamily: 'JetBrains Mono' }
const tip = { contentStyle: { borderRadius: 12, border: '1px solid #E9DED6', fontSize: 12 } }
const hhmm = (ts: string) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(ts) ? ts : ts + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

function TrackRow({ t, onSave }: { t: TrackOut; onSave: (t: TrackOut) => void }) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-sand-200 bg-white p-2.5">
      <Artwork {...artFor(t)} className="h-14 w-14 shrink-0" />
      <div className="min-w-0 flex-1"><p className="truncate font-medium">{t.title}</p><p className="truncate text-xs text-espresso-600">{t.profile.genre} · {t.profile.bpm} BPM · {t.profile.mode_name} · {timeAgo(t.created_at)}</p>
        <audio controls preload="none" src={t.audio_url} className="mt-1 h-8 w-full max-w-xs" aria-label={`Play ${t.title}`} /></div>
      <button className="btn-ghost !px-3 !py-1.5" aria-pressed={t.saved} onClick={() => onSave(t)} aria-label={t.saved ? 'Remove favorite' : 'Save favorite'}>{t.saved ? '♥' : '♡'}</button>
    </li>
  )
}

export default function History() {
  const { user, toast } = useApp()
  const [sessions, setSessions] = useState<SessionOut[] | null>(null)
  const [tracks, setTracks] = useState<TrackOut[] | null>(null)
  const [an, setAn] = useState<Analytics | null>(null)
  const [mood, setMood] = useState<MoodLog[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [detail, setDetail] = useState<SessionOut | null>(null)
  const [busy, setBusy] = useState(false)
  const [tab, setTab] = useState<'all' | 'fav'>('all')

  const load = useCallback(async () => {
    setErr(null)
    try {
      const [s, t, a, m] = await Promise.all([api.sessions(), api.musicHistory(false, 50), api.analytics(), api.moodHistory(200)])
      setSessions(s); setTracks(t); setAn(a); setMood(m)
    } catch (e) { setErr(errMsg(e)) }
  }, [])
  useEffect(() => { if (user) void load() }, [user, load])

  const runDemo = async () => {
    setBusy(true)
    try { const s = await api.createSession({ scenario: 'auto', duration_s: 40 }); toast(`Session #${s.id} created`, 'success'); await load(); setDetail(await api.session(s.id)) } catch (e) { toast(errMsg(e), 'error') } finally { setBusy(false) }
  }
  const open = async (id: number) => { try { setDetail(await api.session(id)) } catch (e) { toast(errMsg(e), 'error') } }
  const toggleSave = async (t: TrackOut) => {
    if (t.id == null) return
    try { await api.saveTrack(t.id, !t.saved); setTracks((x) => x?.map((y) => (y.id === t.id ? { ...y, saved: !y.saved } : y)) ?? x); void api.analytics().then(setAn) } catch (e) { toast(errMsg(e), 'error') }
  }

  if (err) return <div className="container-x py-16"><ErrorState title="Couldn’t load history" message={err} onRetry={() => void load()} /></div>
  const loading = !sessions || !tracks || !an
  const trend = (an?.mood_trend?.length ? an.mood_trend : mood).map((m) => ({ ...m, time: hhmm(m.ts) }))
  const dist = Object.entries(an?.state_distribution ?? {}).map(([k, v]) => ({ state: k, count: v })).sort((a, b) => b.count - a.count)
  const favs = (tracks ?? []).filter((t) => t.saved)
  const shown = tab === 'fav' ? favs : tracks ?? []
  const winData = (detail?.windows ?? []).map((w) => ({ t: w.t0, valence: w.emotion.valence, arousal: w.emotion.arousal, focus: w.emotion.focus, stress: w.emotion.stress }))

  return (
    <div className="container-x py-8 sm:py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="eyebrow">History</p><h1 className="h-display mt-2 text-4xl sm:text-5xl">Your sessions <span className="italic">and sound.</span></h1></div>
        <button className="btn-primary" onClick={() => void runDemo()} disabled={busy}>{busy ? 'Running…' : 'Run a demo session'}</button>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {(['sessions', 'tracks', 'saved', 'feedback', 'mood_logs'] as const).map((k) => (
          <div key={k} className="card p-4"><p className="label-mono">{k.replace('_', ' ')}</p>{loading ? <Skeleton className="mt-2 h-8 w-12" /> : <p className="mt-1 font-display text-3xl">{an!.totals[k]}</p>}</div>
        ))}
      </div>

      <section className="mt-8 grid gap-5 lg:grid-cols-[1.5fr_1fr]" aria-label="Mood trends">
        <div className="card p-5"><h2 className="font-display text-xl">Mood over time</h2>
          {loading ? <Skeleton className="mt-3 h-64" /> : trend.length ? (
            <div className="mt-3 h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={trend} margin={{ left: -24, right: 8, top: 8 }}>
              <CartesianGrid stroke="#E9DED6" vertical={false} /><XAxis dataKey="time" tick={axis} tickLine={false} minTickGap={30} /><YAxis domain={[0, 1]} tick={axis} tickLine={false} axisLine={false} />
              <Tooltip {...tip} formatter={(v: number) => v.toFixed(2)} /><Legend wrapperStyle={{ fontSize: 11 }} />
              {SERIES.map(([k, c]) => <Line key={k} type="monotone" dataKey={k} stroke={c} strokeWidth={k === 'valence' ? 2.2 : 1.6} dot={false} strokeDasharray={k === 'stress' ? '4 3' : undefined} isAnimationActive={false} />)}
            </LineChart></ResponsiveContainer></div>
          ) : <Empty title="No mood data yet">Run a demo session or stream in the Lab to start logging estimated states.</Empty>}
        </div>
        <div className="card p-5"><h2 className="font-display text-xl">State distribution</h2>
          {loading ? <Skeleton className="mt-3 h-64" /> : dist.length ? (
            <div className="mt-3 h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={dist} layout="vertical" margin={{ left: 20, right: 8 }}>
              <XAxis type="number" tick={axis} allowDecimals={false} /><YAxis type="category" dataKey="state" tick={{ ...axis, fontSize: 11 }} width={110} tickLine={false} />
              <Tooltip {...tip} cursor={{ fill: '#F5EFEA' }} /><RBar dataKey="count" fill="#63463B" radius={[0, 6, 6, 0]} isAnimationActive={false} />
            </BarChart></ResponsiveContainer></div>
          ) : <Empty title="Nothing to show yet" />}
        </div>
      </section>

      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="card p-5"><h2 className="font-display text-xl">Before / after mood</h2><p className="text-xs text-espresso-600">From tracks you rated with a post-listening state.</p>
          {an?.mood_shift?.length ? (
            <div className="mt-3 h-60"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ left: -20, right: 10 }}>
              <CartesianGrid stroke="#E9DED6" /><XAxis type="number" dataKey="valence" domain={[0, 1]} name="valence" tick={axis} /><YAxis type="number" dataKey="arousal" domain={[0, 1]} name="arousal" tick={axis} />
              <Tooltip {...tip} /><Legend wrapperStyle={{ fontSize: 11 }} />
              <Scatter name="Before" fill="#2B1B16" data={an.mood_shift.map((m) => m.before)} isAnimationActive={false} /><Scatter name="After" fill="#B08968" data={an.mood_shift.map((m) => m.after)} isAnimationActive={false} />
            </ScatterChart></ResponsiveContainer></div>
          ) : <div className="mt-3"><Empty title="No before/after pairs yet">Rate a generated track in the <Link className="underline" to="/lab#studio">Music Studio</Link> and your post-listening state is recorded here.</Empty></div>}
          {an?.avg_rating != null && <p className="mt-2 font-mono text-xs text-espresso-700">Average rating {an.avg_rating.toFixed(1)} / 5</p>}
        </div>
        <div className="card p-5"><h2 className="font-display text-xl">Target usage</h2>
          {Object.keys(an?.target_usage ?? {}).length ? <div className="mt-3 space-y-2">{Object.entries(an!.target_usage).map(([k, v]) => <div key={k} className="flex items-center gap-3 text-sm"><span className="w-20 capitalize">{k}</span><div className="h-2 flex-1 rounded-full bg-sand-200"><div className="h-full rounded-full bg-espresso-800" style={{ width: `${(v / Math.max(...Object.values(an!.target_usage))) * 100}%` }} /></div><span className="font-mono text-xs">{v}</span></div>)}</div>
            : <div className="mt-3"><Empty title="No targets used yet">Choose Calm, Focus, Energize or Refresh in the Lab to see what you reach for.</Empty></div>}
        </div>
      </section>

      <section className="mt-10" aria-labelledby="hs">
        <h2 id="hs" className="font-display text-2xl">EEG sessions</h2>
        {loading ? <Skeleton className="mt-3 h-28" /> : sessions!.length ? (
          <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{sessions!.map((s) => (
            <li key={s.id}><button onClick={() => void open(s.id)} className={`card card-lift w-full p-4 text-left ${detail?.id === s.id ? '!border-espresso-700' : ''}`}>
              <p className="label-mono">{s.source} · {timeAgo(s.created_at)}</p><p className="mt-1 truncate font-display text-lg">{s.title}</p>
              <p className="mt-1 font-mono text-xs text-espresso-600">{s.duration_s}s · {s.n_windows} windows · {String(s.summary?.dominant_state ?? '')}</p></button></li>
          ))}</ul>
        ) : <div className="mt-3"><Empty title="No EEG sessions yet" cta={<button className="btn-primary" onClick={() => void runDemo()} disabled={busy}>Run a demo session</button>}>Sessions are stored when you upload an EEG file or run a demo session.</Empty></div>}
        {detail && (
          <div className="card mt-5 p-5" aria-live="polite">
            <div className="flex flex-wrap items-baseline justify-between gap-2"><h3 className="font-display text-xl">{detail.title}</h3><span className="font-mono text-xs text-espresso-600">{detail.fs} Hz · {detail.channels.join(' ')} · quality {Number(detail.summary?.mean_quality ?? 0).toFixed(2)}</span></div>
            <div className="mt-3 h-60"><ResponsiveContainer width="100%" height="100%"><AreaChart data={winData} margin={{ left: -24, right: 8 }}>
              <CartesianGrid stroke="#E9DED6" vertical={false} /><XAxis dataKey="t" tick={axis} unit="s" /><YAxis domain={[0, 1]} tick={axis} axisLine={false} />
              <Tooltip {...tip} formatter={(v: number) => v.toFixed(2)} /><Legend wrapperStyle={{ fontSize: 11 }} />
              <Area dataKey="valence" stroke="#2B1B16" fill="#CBB9AC" fillOpacity={0.35} isAnimationActive={false} /><Area dataKey="arousal" stroke="#B08968" fill="none" isAnimationActive={false} />
              <Area dataKey="focus" stroke="#63463B" fill="none" strokeDasharray="4 3" isAnimationActive={false} /><Area dataKey="stress" stroke="#CBB9AC" fill="none" isAnimationActive={false} />
            </AreaChart></ResponsiveContainer></div>
            <p className="mt-2 text-xs text-espresso-600">Per-window estimates (AI-estimated, not clinical).</p>
          </div>
        )}
      </section>

      <section className="mt-10" aria-labelledby="mh">
        <div className="flex items-center justify-between"><h2 id="mh" className="font-display text-2xl">Music</h2>
          <div className="inline-flex rounded-full border border-sand-300 bg-sand-100 p-1">{(['all', 'fav'] as const).map((k) => <button key={k} onClick={() => setTab(k)} aria-pressed={tab === k} className={`rounded-full px-4 py-1 text-sm ${tab === k ? 'bg-espresso-950 text-sand-50' : ''}`}>{k === 'all' ? 'History' : `Favorites (${favs.length})`}</button>)}</div></div>
        {loading ? <Skeleton className="mt-3 h-28" /> : shown.length ? <ul className="mt-3 grid gap-3 lg:grid-cols-2">{shown.map((t) => <TrackRow key={t.audio_id} t={t} onSave={(x) => void toggleSave(x)} />)}</ul>
          : <div className="mt-3"><Empty title={tab === 'fav' ? 'No favorites yet' : 'No tracks generated yet'} cta={<Link to="/lab#studio" className="btn-primary">Open the Music Studio</Link>}>Generate a track and save it with the heart to see it here.</Empty></div>}
      </section>
    </div>
  )
}
