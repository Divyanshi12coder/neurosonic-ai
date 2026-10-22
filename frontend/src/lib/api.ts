// Typed API client mirroring backend/app/schemas.py
export type Scenario = 'auto' | 'calm' | 'focused' | 'stressed' | 'excited' | 'drowsy' | 'melancholic'
export type Target = 'calm' | 'focus' | 'energize' | 'refresh'
export type Mode = 'match' | 'shift'
export type Dim = 'valence' | 'arousal' | 'calmness' | 'focus' | 'stress'
export const DIMS: Dim[] = ['valence', 'arousal', 'calmness', 'focus', 'stress']
export const BANDS = ['delta', 'theta', 'alpha', 'beta', 'gamma'] as const

export interface UserOut { id: number; email: string; display_name: string; is_demo: boolean; created_at: string }
export interface TokenOut { access_token: string; token_type: string; user: UserOut }
export interface Preferences { genres: string[]; default_mode: Mode; default_duration_s: number; store_features: boolean }
export interface ProfileOut { user: UserOut; preferences: Preferences }

export interface Quality { overall: number; per_channel: number[]; label: string }
export interface FeatureImportance {
  feature: string; label: string; value: number; z_score: number; importance: number
  global_importance: number; most_affects: string; direction: string
}
export interface ModelInfo { name?: string; data_source?: string; is_demo_baseline?: boolean; label?: string; [k: string]: unknown }
export interface EmotionEstimate {
  valence: number; arousal: number; calmness: number; focus: number; stress: number; confidence: number
  label: string; quadrant: string; feature_importance: FeatureImportance[]; model: ModelInfo
}
export interface Features {
  band_power: Record<string, number>
  relative_band_power: Record<string, number>
  ratios: Record<string, number>
  frontal_alpha_asymmetry: number
  dominant_frequency: number
  spectral_entropy: number
  signal_variance: number
  temporal?: Record<string, number>
  psd: { freqs: number[]; power: number[] }
  [k: string]: unknown
}
export interface Waveform { fs: number; channels: Record<string, number[]> }
export interface AnalysisOut {
  fs: number; channels: string[]; n_samples: number; duration_s: number; t?: number | null; scenario?: string | null
  simulated_state?: Record<string, number> | null
  quality: Quality; features: Features; waveform: Waveform; emotion: EmotionEstimate
}
export interface WindowSummary { t0: number; quality: number; relative_band_power: Record<string, number>; emotion: Record<string, unknown> & Partial<EmotionEstimate> }
export interface SessionOut {
  id: number; title: string; source: string; scenario: string | null; fs: number; channels: string[]
  duration_s: number; n_windows: number; summary: Record<string, unknown>; windows: WindowSummary[]; created_at: string
}
export interface TextAnalysis {
  provider: string; text: string; emotions: string[]; intent: string | null
  desired_transition: Record<string, string> | null; music_preferences: string[]; context: string[]
  state_estimate: Record<string, number> | null; confidence: number
}
export interface MoodPoint { valence: number; arousal: number; calmness?: number; focus?: number; stress?: number; confidence?: number }
export interface RecommendIn {
  emotion?: MoodPoint | null; mode?: Mode; target?: Target | null; shift?: number; text?: string | null
  prefs?: string[]; session_id?: number | null; quality?: string | null; feature_importance?: unknown[] | null
}
export interface GenerateIn extends RecommendIn { preset_id?: string | null; duration_s?: number; provider?: 'local-synth' | 'huggingface-musicgen'; variation?: number }
export interface Preset {
  id: string; title: string; subtitle: string; genre: string; timbre: string; tags: string[]
  point: Record<string, number>; score: number; fit: number; reasons: string[]; stage?: number | null
}
export interface MusicProfile {
  bpm: number; key: string; scale: string; mode_name: string; energy: number; brightness: number
  rhythm_density: number; harmonic_complexity: number; dynamics: string; texture: string; reverb: number
  instrumentation: string[]; percussion: string; timbre: string; genre: string; mood_tags: string[]
  mood_vector: Record<string, number>
}
export type StatePoint = Partial<Record<Dim, number>>
export interface Plan { mode: Mode; target_key: string | null; current: StatePoint; target: StatePoint; music: StatePoint; shift: number; trajectory: StatePoint[] }
export interface ExplainStep { stage: string; title: string; detail: string }
export interface Explanation { steps: ExplainStep[]; feature_importance: FeatureImportance[]; fusion_weights: Record<string, number>; caveats: string[] }
export interface RecommendOut {
  fused_state: Record<string, number>; fusion_weights: Record<string, number>; plan: Plan; profile: MusicProfile
  trajectory_profiles: MusicProfile[]; mood_vector: Record<string, number>; tracks: Preset[]; playlist: Preset[]
  nlp: TextAnalysis | null; explanation: Explanation; music_session_id?: number | null
}
export interface Artwork { seed: number; palette: string[]; energy: number; brightness: number; bpm: number; valence: number }
export interface TrackOut {
  id: number | null; audio_id: string; audio_url: string; title: string; subtitle: string; preset_id: string
  duration_s: number; provider: string; prompt: string; profile: MusicProfile; artwork: Artwork; saved: boolean; created_at?: string | null
}
export interface GenerateOut { track: TrackOut; recommendation: RecommendOut; provider_note?: string | null }
export interface ChatSource { id?: string; title?: string; source?: string; text?: string; snippet?: string; score?: number; [k: string]: unknown }
export interface ChatOut { answer: string; sources: ChatSource[]; inference: string[]; provider: string; embedder: string; disclaimer: string }
export interface MoodLog { ts: string; valence: number; arousal: number; calmness: number; focus: number; stress: number; label: string; source?: string }
export interface Analytics {
  totals: { sessions: number; tracks: number; saved: number; feedback: number; mood_logs: number }
  mood_trend: MoodLog[]; state_distribution: Record<string, number>; target_usage: Record<string, number>
  avg_rating: number | null
  mood_shift: { track_id: number; title: string; before: { valence: number; arousal: number }; after: { valence: number; arousal: number } }[]
  favorite_tracks: TrackOut[]
}
export interface Health { status: string; version: string; database: string; emotion_model: ModelInfo; llm: string; music_providers: string[]; embedder: string }
export interface Meta { version: string; counts: { endpoints: number; presets: number; channels: number; bands: number; dimensions: number }; [k: string]: unknown }
export type TargetInfo = { valence: number; arousal: number; calmness: number; focus: number; stress: number; label: string; blurb: string }

// ---------------- core ----------------
const TOKEN_KEY = 'neurosonic.token'
export const tokenStore = {
  get(): string | null { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set(t: string) { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* ignore */ } },
  clear() { try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ } },
}

export class ApiError extends Error {
  status: number
  network: boolean
  constructor(message: string, status: number, network = false) { super(message); this.status = status; this.network = network }
}

function detailToText(d: unknown): string {
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => (x && typeof x === 'object' && 'msg' in x ? String((x as { msg: unknown }).msg) : String(x))).join('; ')
  return 'Request failed'
}

async function req<T>(method: string, path: string, body?: unknown, opts: { signal?: AbortSignal; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const tok = tokenStore.get()
  if (tok) headers.Authorization = `Bearer ${tok}`
  let payload: BodyInit | undefined
  if (opts.form) payload = opts.form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  let res: Response
  try {
    res = await fetch(`/api${path}`, { method, headers, body: payload, signal: opts.signal })
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    throw new ApiError('Cannot reach the NeuroSonic backend. Start it with: python -m uvicorn app.main:app --app-dir backend --port 8000', 0, true)
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try { const j = await res.json(); msg = detailToText(j.detail) } catch { /* ignore */ }
    if (res.status === 502 || res.status === 503 || res.status === 504) msg = 'The backend is unreachable or starting up. Please try again in a moment.'
    throw new ApiError(msg, res.status)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// tiny GET cache (ttl ms) with in-flight dedupe
const cache = new Map<string, { at: number; v: unknown }>()
const inflight = new Map<string, Promise<unknown>>()
function cached<T>(key: string, ttl: number, fn: () => Promise<T>): Promise<T> {
  const hit = cache.get(key)
  if (hit && Date.now() - hit.at < ttl) return Promise.resolve(hit.v as T)
  const f = inflight.get(key)
  if (f) return f as Promise<T>
  const p = fn().then((v) => { cache.set(key, { at: Date.now(), v }); inflight.delete(key); return v }, (e) => { inflight.delete(key); throw e })
  inflight.set(key, p)
  return p
}
export const clearCache = () => cache.clear()

export function debounce<A extends unknown[]>(fn: (...a: A) => void, ms: number) {
  let h: ReturnType<typeof setTimeout> | undefined
  const d = (...a: A) => { if (h) clearTimeout(h); h = setTimeout(() => fn(...a), ms) }
  d.cancel = () => { if (h) clearTimeout(h) }
  return d
}

export const api = {
  register: (b: { email: string; password: string; display_name: string }) => req<TokenOut>('POST', '/auth/register', b),
  login: (b: { email: string; password: string }) => req<TokenOut>('POST', '/auth/login', b),
  demoGuest: () => req<TokenOut>('POST', '/auth/demo'),
  demoWindow: (scenario: Scenario, t: number, signal?: AbortSignal, seed = 7, window_s = 4) =>
    req<AnalysisOut>('GET', `/eeg/demo/window?scenario=${scenario}&t=${t}&window_s=${window_s}&seed=${seed}`, undefined, { signal }),
  analyze: (b: { samples: Record<string, number[]>; fs: number }) => req<AnalysisOut>('POST', '/eeg/analyze', b),
  upload: (file: File, fs?: number, title?: string) => {
    const f = new FormData(); f.append('file', file)
    if (fs) f.append('fs', String(fs))
    if (title) f.append('title', title)
    return req<SessionOut>('POST', '/eeg/upload', undefined, { form: f })
  },
  createSession: (b: { title?: string; scenario?: Scenario; duration_s?: number; seed?: number }) => req<SessionOut>('POST', '/eeg/session', b),
  sessions: () => req<SessionOut[]>('GET', '/eeg/sessions'),
  session: (id: number) => req<SessionOut>('GET', `/eeg/session/${id}`),
  moodHistory: (limit = 200) => req<MoodLog[]>('GET', `/mood/history?limit=${limit}`),
  parseText: (text: string) => req<TextAnalysis>('POST', '/nlp/parse', { text }),
  recommend: (b: RecommendIn, signal?: AbortSignal) => req<RecommendOut>('POST', '/music/recommend', b, { signal }),
  generate: (b: GenerateIn) => req<GenerateOut>('POST', '/music/generate', b),
  catalog: () => cached('catalog', 600000, () => req<Preset[]>('GET', '/music/catalog')),
  targets: () => cached('targets', 600000, () => req<Record<string, TargetInfo>>('GET', '/music/targets')),
  saveTrack: (track_id: number, saved = true) => req<unknown>('POST', '/music/save', { track_id, saved }),
  feedback: (b: { track_id: number; rating: number; mood_after?: MoodPoint | null; comment?: string | null }) => req<unknown>('POST', '/music/feedback', b),
  musicHistory: (saved_only = false, limit = 50) => req<TrackOut[]>('GET', `/music/history?saved_only=${saved_only}&limit=${limit}`),
  profile: () => req<ProfileOut>('GET', '/user/profile'),
  setPrefs: (b: Preferences) => req<Preferences>('PUT', '/user/preferences', b),
  analytics: () => req<Analytics>('GET', '/user/analytics'),
  chat: (b: { message: string; context?: { emotion?: unknown; profile?: unknown } | null }) => req<ChatOut>('POST', '/guide/chat', b),
  suggestions: () => cached('suggest', 600000, () => req<string[]>('GET', '/guide/suggestions')),
  health: () => req<Health>('GET', '/health'),
  meta: () => cached('meta', 60000, () => req<Meta>('GET', '/meta')),
}

export function errMsg(e: unknown): string { return e instanceof Error ? e.message : 'Something went wrong' }
