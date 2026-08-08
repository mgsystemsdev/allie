import { useCallback, useEffect, useState } from 'react'
import {
  api,
  clearToken,
  getToken,
  setToken,
  type AnimalOverview,
  type Feed,
} from './api/client'
import { JournalTab, LocalTab, PhotosTab, SettingsTab } from './components/ExtrasTabs'
import { FeedingTab } from './components/FeedingTab'
import { HabitatTab } from './components/HabitatTab'
import { HandlingTab } from './components/HandlingTab'
import { HealthTab } from './components/HealthTab'
import { OverviewTab } from './components/OverviewTab'
import { PreyTab, SpeciesTab } from './components/StaticTabs'
import { Btn, Field, Input } from './components/ui'
import { useCountdown } from './hooks/useCountdown'

type TabId =
  | 'overview'
  | 'feeding'
  | 'handling'
  | 'prey'
  | 'habitat'
  | 'health'
  | 'journal'
  | 'photos'
  | 'species'
  | 'settings'
  | 'local'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'feeding', label: 'Feeding' },
  { id: 'handling', label: 'Handling' },
  { id: 'prey', label: 'Prey Guide' },
  { id: 'habitat', label: 'Habitat' },
  { id: 'health', label: 'Health' },
  { id: 'journal', label: 'Journal' },
  { id: 'photos', label: 'Photos' },
  { id: 'species', label: 'Species Info' },
  { id: 'settings', label: 'Settings' },
  // Local tools only while developing — hidden in Railway production builds
  ...(import.meta.env.DEV ? [{ id: 'local' as const, label: 'Local' }] : []),
]

function Login({ onOk }: { onOk: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  return (
    <div className="w-full max-w-md rounded-2xl border border-border bg-charcoal p-8">
      <h1 className="font-display text-3xl font-bold text-bone">Allie</h1>
      <p className="mt-1 font-mono text-[11px] tracking-wide text-muted">Bredli Care Dashboard</p>
      <form
        className="mt-6 space-y-3"
        onSubmit={async (e) => {
          e.preventDefault()
          setBusy(true)
          setError('')
          try {
            const { token } = await api.login(password)
            setToken(token)
            onOk()
          } catch {
            setError('Invalid password')
          } finally {
            setBusy(false)
          }
        }}
      >
        <Field label="Password">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
        </Field>
        {error && <p className="text-[13px] text-[#E06050]">{error}</p>}
        <Btn type="submit" disabled={busy}>
          Enter
        </Btn>
      </form>
    </div>
  )
}

function formatDob(iso: string) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken())
  const [tab, setTab] = useState<TabId>('overview')
  const [animal, setAnimal] = useState<AnimalOverview | null>(null)
  const [feeds, setFeeds] = useState<Feed[]>([])
  const [clock, setClock] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      const [a, f] = await Promise.all([api.animal(), api.feeds.list()])
      setAnimal(a)
      setFeeds(f)
      setError('')
    } catch (e) {
      if (String(e).includes('Unauthorized')) {
        setAuthed(false)
        return
      }
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    if (authed) void refresh()
  }, [authed, refresh])

  useEffect(() => {
    const tick = () => {
      const now = new Date()
      setClock(
        now.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) +
          ' · ' +
          now.toLocaleTimeString('en-GB', { hour12: false }),
      )
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  const handleTimer = useCountdown(
    animal?.clear_to_handle.clear_at,
    animal?.clear_to_handle.ready ?? true,
  )

  useEffect(() => {
    if (!animal) return
    if (!animal.clear_to_handle.ready && handleTimer.done && animal.clear_to_handle.clear_at) {
      void refresh()
    }
  }, [handleTimer.done, animal, refresh])

  if (!authed) {
    return <Login onOk={() => setAuthed(true)} />
  }

  if (!animal) {
    return (
      <div className="w-full max-w-[1100px] rounded-2xl border border-border bg-charcoal p-8 text-muted">
        {error || 'Loading…'}
      </div>
    )
  }

  return (
    <div className="w-full max-w-[1100px] overflow-hidden rounded-2xl border border-border bg-charcoal text-bone">
      <header className="border-b border-border-hi bg-gradient-to-br from-bark to-[#1e1208] px-6 pb-4 pt-5">
        <div className="mb-3.5 flex items-start justify-between gap-3">
          <div>
            <div className="font-display text-[28px] font-bold leading-tight text-bone">{animal.name}</div>
            <div className="mt-0.5 font-mono text-[11px] tracking-wide text-muted">
              {animal.species} · {animal.common_name}
            </div>
            <div className="mt-1 text-[13px] text-bone-dark">
              Owner: <span className="text-sand">{animal.owner}</span>
            </div>
            <div className="mt-1.5 inline-block rounded-full border border-[#7a3a5a] bg-[#3a1a2a] px-2.5 py-1 font-mono text-[11px] text-[#D090B0]">
              ♀ {animal.sex}
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="inline-block whitespace-nowrap rounded-full border border-olive bg-[#1a3a20] px-2.5 py-1 font-mono text-[11px] text-sage">
              ● {animal.status}
            </div>
            <div
              className={`mt-1.5 inline-block whitespace-nowrap rounded-full border px-2.5 py-1 font-mono text-[11px] ${
                animal.clear_to_handle.ready
                  ? 'border-olive bg-[#1a3a20] text-sage'
                  : 'border-[#D4A040] bg-[#3a2a10] text-[#E8C080]'
              }`}
            >
              {animal.clear_to_handle.ready
                ? 'Clear to handle'
                : `Wait ${handleTimer.label || animal.clear_to_handle.countdown || '…'}`}
            </div>
            <div className="mt-1.5 font-mono text-[11px] tracking-wide text-muted">{clock}</div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2.5">
          <div className="min-w-[120px] flex-[2] rounded-[10px] border border-border-hi bg-charcoal px-3 py-2.5 text-center">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">Date of birth</div>
            <div className="font-mono text-[14px] text-bone-dark">{formatDob(animal.dob)}</div>
          </div>
          <div className="min-w-[72px] flex-1 rounded-[10px] border border-border-hi bg-charcoal px-3 py-2.5 text-center">
            <div className="font-display text-[26px] font-bold leading-none text-sand">{animal.age.months}</div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Months old</div>
          </div>
          <div
            className={`min-w-[90px] flex-1 rounded-[10px] border bg-charcoal px-3 py-2.5 text-center ${
              animal.next_feed && animal.next_feed.days_until < 0
                ? 'border-[#E06050]'
                : animal.next_feed && animal.next_feed.days_until <= 2
                  ? 'border-[#D4A040]'
                  : 'border-border-hi'
            }`}
          >
            <div
              className={`font-display text-[18px] font-bold leading-none ${
                animal.next_feed && animal.next_feed.days_until < 0
                  ? 'text-[#E06050]'
                  : animal.next_feed && animal.next_feed.days_until <= 2
                    ? 'text-[#D4A040]'
                    : 'text-sand'
              }`}
            >
              {animal.next_feed?.due_date?.slice(5) || '—'}
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Next feed</div>
            <div
              className={`mt-1 font-display text-[18px] font-bold leading-none ${
                animal.next_feed && animal.next_feed.days_until < 0
                  ? 'text-[#E06050]'
                  : animal.next_feed && animal.next_feed.days_until <= 2
                    ? 'text-[#D4A040]'
                    : 'text-sand'
              }`}
            >
              {animal.next_feed
                ? animal.next_feed.days_until < 0
                  ? `${Math.abs(animal.next_feed.days_until)}d overdue`
                  : animal.next_feed.days_until === 0
                    ? 'Due today'
                    : `In ${animal.next_feed.days_until}d`
                : 'Log a feed'}
            </div>
          </div>
          <div
            className={`min-w-[90px] flex-1 rounded-[10px] border bg-charcoal px-3 py-2.5 text-center ${
              animal.next_maintenance && animal.next_maintenance.days_until < 0
                ? 'border-[#E06050]'
                : animal.next_maintenance && animal.next_maintenance.days_until <= 1
                  ? 'border-[#D4A040]'
                  : 'border-border-hi'
            }`}
          >
            <div
              className={`font-display text-[18px] font-bold leading-none ${
                animal.next_maintenance && animal.next_maintenance.days_until < 0
                  ? 'text-[#E06050]'
                  : 'text-sand'
              }`}
            >
              {animal.next_maintenance?.due_date?.slice(5) || '—'}
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Next maint.</div>
            <div className="mt-0.5 text-[10px] text-muted">
              {animal.next_maintenance
                ? `${animal.next_maintenance.label}${
                    animal.next_maintenance.days_until < 0
                      ? ` · ${Math.abs(animal.next_maintenance.days_until)}d overdue`
                      : animal.next_maintenance.days_until === 0
                        ? ' · today'
                        : ` · in ${animal.next_maintenance.days_until}d`
                  }`
                : '—'}
            </div>
          </div>
          <div
            className={`min-w-[90px] flex-1 rounded-[10px] border bg-charcoal px-3 py-2.5 text-center ${
              animal.handling_gap.overdue ? 'border-[#D4A040]' : 'border-border-hi'
            }`}
          >
            <div
              className={`font-display text-[18px] font-bold leading-none ${
                animal.handling_gap.overdue ? 'text-[#D4A040]' : 'text-sand'
              }`}
            >
              {animal.handling_gap.last_date?.slice(5) || '—'}
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Last han.</div>
            <div className="mt-0.5 text-[10px] text-muted">
              {animal.handling_gap.last_date == null
                ? 'None logged'
                : animal.handling_gap.days_since === 0
                  ? 'Today'
                  : animal.handling_gap.overdue
                    ? `${animal.handling_gap.days_since}d · overdue`
                    : `${animal.handling_gap.days_since}d ago`}
            </div>
          </div>
          <div className="min-w-[90px] flex-1 rounded-[10px] border border-border-hi bg-charcoal px-3 py-2.5 text-center">
            <div className="font-display text-[18px] font-bold leading-none text-sand">
              {animal.last_shed?.date?.slice(5) || '—'}
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Last shed</div>
            <div className="mt-0.5 text-[10px] text-muted">{animal.last_shed?.quality || 'None logged'}</div>
          </div>
        </div>
        <div className="mt-2.5">
          <span className="inline-block rounded-full border border-sand bg-[#4a2c14] px-3 py-1 font-mono text-[11px] text-sand">
            {animal.stage.label} · {animal.stage.desc}
          </span>
        </div>
      </header>

      <nav className="flex gap-0 overflow-x-auto border-b border-border bg-[#1e1208] scrollbar-none">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-bold uppercase tracking-[0.08em] transition ${
              tab === t.id
                ? 'border-sand text-sand'
                : 'border-transparent text-muted hover:text-bone-dark'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="px-6 pb-7 pt-5">
        {tab === 'overview' && <OverviewTab animal={animal} feeds={feeds} onChange={refresh} />}
        {tab === 'feeding' && <FeedingTab animal={animal} onChange={refresh} />}
        {tab === 'handling' && <HandlingTab animal={animal} onChange={refresh} />}
        {tab === 'prey' && <PreyTab animal={animal} />}
        {tab === 'habitat' && <HabitatTab />}
        {tab === 'health' && <HealthTab onChange={refresh} />}
        {tab === 'journal' && <JournalTab />}
        {tab === 'photos' && <PhotosTab />}
        {tab === 'species' && <SpeciesTab />}
        {tab === 'settings' && (
          <SettingsTab
            onLogout={() => {
              clearToken()
              setAuthed(false)
            }}
          />
        )}
        {import.meta.env.DEV && tab === 'local' && <LocalTab />}
      </main>
    </div>
  )
}
