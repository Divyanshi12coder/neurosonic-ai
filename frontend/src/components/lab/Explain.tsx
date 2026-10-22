import type { RecommendOut } from '../../lib/api'
import { Bar } from '../ui'

export function Explain({ rec }: { rec: RecommendOut | null }) {
  const ex = rec?.explanation
  if (!ex) return <p className="text-sm text-espresso-600">Waiting for a recommendation…</p>
  const fi = [...(ex.feature_importance ?? [])].sort((a, b) => b.importance - a.importance).slice(0, 8)
  return (
    <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
      <div className="card p-5 sm:p-6">
        <ol className="space-y-0">
          {ex.steps.map((s, i) => (
            <li key={i} className="relative flex gap-4 pb-6 last:pb-0">
              {i < ex.steps.length - 1 && <span aria-hidden className="absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-px bg-sand-300" />}
              <span className="z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-espresso-950 font-mono text-xs text-sand-50">{i + 1}</span>
              <div className="min-w-0">
                <p className="label-mono">{s.stage}</p>
                <p className="font-display text-xl">{s.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-espresso-700">{s.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
      <div className="space-y-5">
        <div className="card p-5">
          <h3 className="font-display text-lg">Feature importance</h3>
          <p className="mb-3 text-xs text-espresso-600">Local perturbation estimates for this model.</p>
          {fi.length ? <div className="space-y-2.5">{fi.map((f) => (
            <Bar key={f.feature} label={f.label} value={f.importance} right={`${f.direction} ${f.most_affects}`} tone={f.direction === 'raises' ? 'dark' : 'clay'} />
          ))}</div> : <p className="text-sm text-espresso-600">Feature attributions appear when an EEG state is available.</p>}
        </div>
        <div className="card p-5">
          <h3 className="font-display text-lg">Fusion weights</h3>
          <div className="mt-3 space-y-2.5">{Object.entries(ex.fusion_weights ?? {}).map(([k, v]) => <Bar key={k} label={k === 'eeg' ? 'EEG signal' : k === 'language' ? 'Your words' : k} value={v} right={`${Math.round(v * 100)}%`} tone="clay" />)}</div>
        </div>
        <div className="rounded-2xl border border-sand-300 bg-sand-100 p-5">
          <h3 className="label-mono">Caveats</h3>
          <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-espresso-700">{ex.caveats.map((c, i) => <li key={i}>• {c}</li>)}</ul>
        </div>
      </div>
    </div>
  )
}
