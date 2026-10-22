import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api, clearCache, errMsg, tokenStore, type EmotionEstimate, type MusicProfile, type UserOut } from '../lib/api'

type ToastKind = 'info' | 'success' | 'error'
interface Toast { id: number; kind: ToastKind; text: string }

export interface SharedContext {
  emotion: Pick<EmotionEstimate, 'valence' | 'arousal' | 'calmness' | 'focus' | 'stress' | 'confidence' | 'label' | 'quadrant'> | null
  profile: MusicProfile | null
  scenario?: string | null
}

interface AppState {
  user: UserOut | null
  authReady: boolean
  authError: string | null
  setAuth: (t: string, u: UserOut) => void
  logout: () => Promise<void>
  retryAuth: () => void
  toast: (text: string, kind?: ToastKind) => void
  shared: SharedContext
  setShared: (p: Partial<SharedContext>) => void
}

const Ctx = createContext<AppState | null>(null)
export const useApp = () => {
  const c = useContext(Ctx)
  if (!c) throw new Error('useApp outside provider')
  return c
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [authReady, setReady] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [shared, setSharedState] = useState<SharedContext>({ emotion: null, profile: null })
  const tid = useRef(0)

  const toast = useCallback((text: string, kind: ToastKind = 'info') => {
    const id = ++tid.current
    setToasts((t) => [...t.slice(-3), { id, kind, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 6500 : 3500)
  }, [])

  const setAuth = useCallback((t: string, u: UserOut) => { tokenStore.set(t); clearCache(); setUser(u) }, [])

  const boot = useCallback(async () => {
    setAuthError(null)
    try {
      if (tokenStore.get()) {
        try { const p = await api.profile(); setUser(p.user); setReady(true); return } catch (e) {
          if (!(e as { status?: number }).status || (e as { status: number }).status !== 401) { if ((e as { network?: boolean }).network) throw e }
          tokenStore.clear()
        }
      }
      const t = await api.demoGuest()
      setAuth(t.access_token, t.user)
    } catch (e) {
      setAuthError(errMsg(e))
    } finally { setReady(true) }
  }, [setAuth])

  useEffect(() => { void boot() }, [boot])

  const logout = useCallback(async () => {
    tokenStore.clear(); clearCache(); setUser(null)
    try { const t = await api.demoGuest(); setAuth(t.access_token, t.user) } catch (e) { setAuthError(errMsg(e)) }
  }, [setAuth])

  const setShared = useCallback((p: Partial<SharedContext>) => setSharedState((s) => ({ ...s, ...p })), [])

  const value = useMemo<AppState>(() => ({ user, authReady, authError, setAuth, logout, retryAuth: boot, toast, shared, setShared }),
    [user, authReady, authError, setAuth, logout, boot, toast, shared, setShared])

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2" role="status" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div key={t.id} layout initial={{ opacity: 0, y: 16, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, x: 30 }}
              className={`pointer-events-auto rounded-xl border px-4 py-3 text-sm shadow-lift ${t.kind === 'error' ? 'border-espresso-700 bg-espresso-900 text-sand-50' : t.kind === 'success' ? 'border-sand-300 bg-white text-espresso-950' : 'border-sand-300 bg-sand-100 text-espresso-900'}`}>
              {t.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  )
}
