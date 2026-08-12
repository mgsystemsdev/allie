import { useEffect, useMemo, useState } from 'react'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  api,
  mediaUrl,
  type AnimalOverview,
  type EnvReading,
  type Feed,
  type Handling,
  type Maint,
  type Photo,
  type Regurg,
  type ShedCycle,
  type Weight,
} from '../api/client'
import { Empty, SectionLabel } from './ui'

type Point = { date: string; label: string; tone?: 'ok' | 'warn' }

function Track({ label, points }: { label: string; points: Point[] }) {
  const sorted = useMemo(() => [...points].sort((a, b) => a.date.localeCompare(b.date)), [points])
  if (!sorted.length) return null
  return (
    <section>
      <SectionLabel>{label}</SectionLabel>
      <div className="flex gap-4 overflow-x-auto pb-1 scrollbar-none">
        {sorted.map((p, i) => (
          <div key={`${p.date}-${p.label}-${i}`} className="w-16 shrink-0 text-center">
            <div
              className={`mx-auto h-2 w-2 rounded-full ${p.tone === 'ok' ? 'bg-sage' : p.tone === 'warn' ? 'bg-sand' : 'bg-olive'}`}
            />
            <div className="mt-1.5 font-mono text-[10px] text-muted">{p.date.slice(5)}</div>
            <div className="mt-0.5 text-[11px] leading-tight text-bone">{p.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function daysBetween(a: string, b: string) {
  const ms = new Date(b + 'T00:00:00').getTime() - new Date(a + 'T00:00:00').getTime()
  return Math.round(ms / 86400000)
}

export function StatsTab({ animal, onChange }: { animal: AnimalOverview; onChange: () => void }) {
  const [feeds, setFeeds] = useState<Feed[]>([])
  const [weights, setWeights] = useState<Weight[]>([])
  const [handlings, setHandlings] = useState<Handling[]>([])
  const [sheds, setSheds] = useState<ShedCycle[]>([])
  const [env, setEnv] = useState<EnvReading[]>([])
  const [maint, setMaint] = useState<Maint[]>([])
  const [photos, setPhotos] = useState<Photo[]>([])
  const [regurgs, setRegurgs] = useState<Regurg[]>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const [f, w, h, s, e, m, p, r] = await Promise.all([
        api.feeds.list(),
        api.weights.list(),
        api.handlings.list(),
        api.shedCycles.list(),
        api.envReadings.list(),
        api.maintenance.list(),
        api.photos.list(),
        api.regurgitations.list(),
      ])
      if (cancelled) return
      setFeeds(f)
      setWeights(w)
      setHandlings(h)
      setSheds(s)
      setEnv(e)
      setMaint(m)
      setPhotos([...p].sort((a, b) => a.taken_at.localeCompare(b.taken_at)))
      setRegurgs(r)
      setLoaded(true)
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [animal.id])

  const feedPoints: Point[] = useMemo(() => {
    const ordered = [...feeds].sort((a, b) => a.date.localeCompare(b.date))
    return ordered.map((f, i) => {
      const prev = ordered[i - 1]
      const gap = prev ? daysBetween(prev.date, f.date) : null
      return {
        date: f.date,
        label: f.accepted ? (gap != null ? `${gap}d ok` : 'ok') : 'refused',
        tone: f.accepted ? 'ok' : 'warn',
      }
    })
  }, [feeds])

  const handlePoints: Point[] = useMemo(() => {
    const ordered = [...handlings].sort((a, b) => a.date.localeCompare(b.date))
    return ordered.map((h, i) => {
      const prev = ordered[i - 1]
      const gap = prev ? daysBetween(prev.date, h.date) : null
      return { date: h.date, label: gap != null ? `${gap}d` : `${h.duration_min}m` }
    })
  }, [handlings])

  const shedPoints: Point[] = useMemo(
    () =>
      [...sheds]
        .sort((a, b) => a.started_at.localeCompare(b.started_at))
        .map((s) => ({ date: s.started_at, label: s.status })),
    [sheds],
  )

  const maintPoints: Point[] = useMemo(
    () =>
      [...maint]
        .sort((a, b) => a.date.localeCompare(b.date))
        .map((m) => ({
          date: m.date,
          label: m.kind === 'deep_clean' ? 'deep' : m.kind === 'substrate' ? 'sub' : 'water',
        })),
    [maint],
  )

  const envChart = useMemo(
    () =>
      [...env]
        .sort((a, b) => a.recorded_at.localeCompare(b.recorded_at))
        .map((r) => ({
          date: r.recorded_at.slice(0, 10),
          hot: r.temp_hot_f,
          cool: r.temp_cool_f,
          rh: r.humidity_pct,
        })),
    [env],
  )

  const empty =
    loaded &&
    !feeds.length &&
    !weights.length &&
    !handlings.length &&
    !sheds.length &&
    !env.length &&
    !maint.length &&
    !photos.length &&
    !regurgs.length

  if (!loaded) {
    return <p className="text-[13px] text-muted">Loading upkeep…</p>
  }
  if (empty) {
    return <Empty>Log care to see upkeep over time.</Empty>
  }

  const weightSorted = [...weights].sort((a, b) => a.date.localeCompare(b.date))

  return (
    <div>
      <section>
        <SectionLabel>Photos</SectionLabel>
        {photos.length === 0 ? (
          <p className="text-[13px] text-muted">No photos yet.</p>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-none">
            {photos.map((p) => {
              const hero = p.id === animal.hero_photo_id
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => void api.setHero(hero ? null : p.id).then(() => onChange())}
                  className={`shrink-0 text-left ${hero ? 'ring-2 ring-sand ring-offset-2 ring-offset-charcoal' : ''}`}
                  aria-pressed={hero}
                  title={hero ? 'Current profile — tap to clear' : 'Set as profile'}
                >
                  <img
                    src={mediaUrl(p.url)}
                    alt={p.caption || p.kind}
                    className="h-20 w-20 rounded-[8px] border border-border-hi object-cover"
                  />
                  <div className="mt-1 font-mono text-[10px] text-muted">{p.taken_at.slice(5)}</div>
                </button>
              )
            })}
          </div>
        )}
      </section>

      <section>
        <SectionLabel>Weight</SectionLabel>
        {weightSorted.length === 0 ? (
          <p className="text-[13px] text-muted">No weights yet.</p>
        ) : (
          <>
            <p className="mb-2 text-[13px] text-bone">
              {animal.current_weight_g != null ? `${animal.current_weight_g}g` : '—'}
              {weightSorted.length > 1 ? (
                <span className="text-muted">
                  {' '}
                  · {weightSorted[weightSorted.length - 1].weight_g - weightSorted[0].weight_g >= 0 ? '+' : ''}
                  {(weightSorted[weightSorted.length - 1].weight_g - weightSorted[0].weight_g).toFixed(0)}g since first log
                </span>
              ) : null}
            </p>
            <div className="mb-2 h-[180px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weightSorted.map((w) => ({ date: w.date, weight: w.weight_g }))}>
                  <XAxis dataKey="date" stroke="#737373" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#737373" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #d4d4d4', color: '#000000' }}
                  />
                  <Line type="monotone" dataKey="weight" stroke="#404040" strokeWidth={2} dot={{ fill: '#404040' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>

      <Track label="Feeding rhythm" points={feedPoints} />
      <Track label="Handling" points={handlePoints} />
      <Track
        label={
          animal.shed_prediction?.median_days != null
            ? `Shed · median ${animal.shed_prediction.median_days}d`
            : 'Shed'
        }
        points={shedPoints}
      />

      <section>
        <SectionLabel>Habitat</SectionLabel>
        {envChart.length === 0 ? (
          <p className="text-[13px] text-muted">No readings yet.</p>
        ) : (
          <>
            <p className="mb-2 text-[12px] text-muted">Targets · hot 90–95°F · cool 75–79°F · RH 40–60%</p>
            <div className="h-[160px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={envChart}>
                  <XAxis dataKey="date" stroke="#737373" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#737373" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#ffffff', border: '1px solid #d4d4d4', color: '#000000' }}
                  />
                  <Line type="monotone" dataKey="hot" stroke="#404040" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="cool" stroke="#737373" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="rh" stroke="#525252" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>

      <Track label="Maintenance" points={maintPoints} />
      <Track
        label="Regurg"
        points={regurgs.map((r) => ({ date: r.date, label: r.severity, tone: 'warn' as const }))}
      />
    </div>
  )
}
