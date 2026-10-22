import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errMsg } from '../lib/api'
import { useApp } from '../store/app'
import { BrainContour } from '../components/Illustrations'

export default function Login() {
  const { setAuth, toast, user } = useApp()
  const nav = useNavigate()
  const [reg, setReg] = useState(false)
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const run = async (fn: () => Promise<{ access_token: string; user: import('../lib/api').UserOut }>, msg: string) => {
    setBusy(true); setErr(null)
    try { const t = await fn(); setAuth(t.access_token, t.user); toast(msg, 'success'); nav('/lab') } catch (e) { setErr(errMsg(e)) } finally { setBusy(false) }
  }
  return (
    <div className="container-x grid items-center gap-10 py-12 lg:grid-cols-2 lg:py-20">
      <div className="hidden lg:block"><p className="eyebrow">Welcome</p><h1 className="h-display mt-3 text-5xl">Your sessions, <span className="italic">remembered.</span></h1>
        <p className="mt-4 max-w-md text-espresso-700">Create an account to keep EEG sessions, tracks and mood trends, or try everything instantly as a guest.</p><BrainContour className="mt-8 w-full max-w-sm" /></div>
      <div className="card mx-auto w-full max-w-md p-6 sm:p-8">
        <h2 className="font-display text-3xl">{reg ? 'Create account' : 'Sign in'}</h2>
        {user && <p className="mt-1 text-xs text-espresso-600">Currently: {user.is_demo ? 'demo guest' : user.display_name}</p>}
        <button className="btn-primary mt-5 w-full" disabled={busy} onClick={() => void run(api.demoGuest, 'Welcome, guest')}>Continue as demo guest</button>
        <div className="my-5 flex items-center gap-3 text-xs text-espresso-600"><span className="h-px flex-1 bg-sand-200" />or with email<span className="h-px flex-1 bg-sand-200" /></div>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); void run(() => reg ? api.register({ email, password: pw, display_name: name }) : api.login({ email, password: pw }), reg ? 'Account created' : 'Signed in') }}>
          {reg && <label className="block"><span className="label-mono">Display name</span><input className="input mt-1" required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></label>}
          <label className="block"><span className="label-mono">Email</span><input className="input mt-1" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></label>
          <label className="block"><span className="label-mono">Password {reg && '(min 8 characters)'}</span><input className="input mt-1" type="password" required minLength={reg ? 8 : 1} maxLength={72} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete={reg ? 'new-password' : 'current-password'} /></label>
          {err && <p role="alert" className="rounded-lg border border-sand-300 bg-sand-100 px-3 py-2 text-sm">{err}</p>}
          <button className="btn-ghost w-full" disabled={busy} type="submit">{reg ? 'Create account' : 'Sign in'}</button>
        </form>
        <button className="mt-4 w-full text-center text-sm text-espresso-700 underline" onClick={() => { setReg(!reg); setErr(null) }}>{reg ? 'Have an account? Sign in' : 'New here? Create an account'}</button>
      </div>
    </div>
  )
}
