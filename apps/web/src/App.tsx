import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  clearToken,
  getToken,
  mediaUrl,
  setToken,
  todayStr,
  type AnimalOverview,
  type Feed,
} from './api/client'
import { JournalTab, LocalTab, PhotosTab, SettingsTab } from './components/ExtrasTabs'
import { FeedingTab } from './components/FeedingTab'
import { HabitatTab } from './components/HabitatTab'
import { HandlingTab } from './components/HandlingTab'
import { HealthTab } from './components/HealthTab'
import { LogsTab } from './components/LogsTab'
import { OverviewTab } from './components/OverviewTab'
import { PreyTab, SpeciesTab } from './components/StaticTabs'
import { StatsTab } from './components/StatsTab'
import { Btn, Field, Input } from './components/ui'
import { useCountdown } from './hooks/useCountdown'

type TabId =
  | 'overview'
  | 'logs'
  | 'stats'
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
  { id: 'logs', label: 'Logs' },
  { id: 'stats', label: 'Stats' },
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
    <div className="w-full max-w-md rounded-none border-0 bg-charcoal p-6 sm:rounded-2xl sm:border sm:border-border sm:p-8">
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
        {error && <p className="text-[13px] text-bone">{error}</p>}
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

/** Days until next birthday (0 = today). */
function daysUntilBirthday(dobIso: string): number {
  const dob = new Date(dobIso + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  let next = new Date(today.getFullYear(), dob.getMonth(), dob.getDate())
  if (next < today) {
    next = new Date(today.getFullYear() + 1, dob.getMonth(), dob.getDate())
  }
  return Math.round((next.getTime() - today.getTime()) / 86400000)
}

function HeroPortrait({
  name,
  url,
  onChanged,
}: {
  name: string
  url: string | null | undefined
  onChanged: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  async function upload(file: File) {
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('taken_at', todayStr())
      form.append('kind', 'other')
      form.append('caption', 'Profile')
      const photo = await api.photos.upload(form)
      await api.setHero(photo.id)
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) void upload(file)
        }}
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        aria-label={url ? `Change ${name}'s profile photo` : `Add ${name}'s profile photo`}
        title={url ? 'Change profile photo' : 'Add profile photo'}
        className={`relative shrink-0 overflow-hidden rounded-[10px] border border-border-hi focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sand disabled:opacity-60 ${
          busy ? 'opacity-60' : ''
        }`}
      >
        {url ? (
          <img
            src={mediaUrl(url)}
            alt=""
            className="h-16 w-16 object-cover sm:h-[88px] sm:w-[88px]"
          />
        ) : (
          <div className="flex h-16 w-16 items-center justify-center bg-bark font-display text-xl text-muted sm:h-[88px] sm:w-[88px]">
            {name.slice(0, 1)}
          </div>
        )}
        <span className="pointer-events-none absolute inset-x-0 bottom-0 bg-bone/70 py-0.5 text-center font-mono text-[9px] uppercase tracking-wide text-inverse">
          {busy ? '…' : url ? 'Change' : 'Add'}
        </span>
      </button>
    </>
  )
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
      <div className="w-full max-w-[1100px] bg-charcoal p-8 text-muted sm:rounded-2xl sm:border sm:border-border">
        {error || 'Loading…'}
      </div>
    )
  }

  const bdayIn = daysUntilBirthday(animal.dob)

  return (
    <div className="w-full max-w-[1100px] overflow-hidden bg-charcoal text-bone sm:rounded-2xl sm:border sm:border-border">
      <header className="border-b border-border-hi bg-charcoal px-4 pb-4 pt-4 sm:px-6 sm:pt-5">
        <div className="mb-3.5 flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <HeroPortrait name={animal.name} url={animal.hero_photo_url} onChanged={refresh} />
            <div className="min-w-0">
            <div className="font-display text-[24px] font-bold leading-tight text-bone sm:text-[28px]">{animal.name}</div>
            <div className="mt-0.5 font-mono text-[11px] tracking-wide text-muted">
              {animal.species} · {animal.common_name}
            </div>
            <div className="mt-1 text-[13px] text-bone-dark">
              Owner: <span className="text-sand">{animal.owner}</span>
            </div>
            <div className="mt-1.5 inline-block rounded-full border border-border-hi bg-bark px-2.5 py-1 font-mono text-[11px] text-sand">
              ♀ {animal.sex}
            </div>
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="inline-block whitespace-nowrap rounded-full border border-olive bg-bark px-2.5 py-1 font-mono text-[11px] text-sage">
              ● {animal.status}
            </div>
            <div
              className={`mt-1.5 inline-block whitespace-nowrap rounded-full border px-2.5 py-1 font-mono text-[11px] ${
                animal.clear_to_handle.ready
                  ? 'border-olive bg-bark text-sage'
                  : 'border-sand bg-bark text-sand'
              }`}
            >
              {animal.clear_to_handle.ready
                ? 'Clear to handle'
                : `Wait ${handleTimer.label || animal.clear_to_handle.countdown || '…'}`}
            </div>
            <div className="mt-1.5 font-mono text-[11px] tracking-wide text-muted">{clock}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:gap-2.5">
          <div className="col-span-2 min-w-0 rounded-[10px] border border-border-hi bg-bark px-3 py-2.5 text-center sm:min-w-[140px] sm:flex-[2]">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted">Date of birth</div>
            <div className="font-mono text-[14px] text-bone-dark">{formatDob(animal.dob)}</div>
            <div
              className={`mt-1.5 font-display text-[16px] font-bold leading-none ${
                bdayIn === 0 ? 'text-bone' : 'text-sand'
              }`}
            >
              {bdayIn === 0
                ? `${animal.age.months} mo · birthday today`
                : `${animal.age.months} mo · birthday in ${bdayIn}d`}
            </div>
          </div>
          <div
            className={`min-w-0 rounded-[10px] border bg-bark px-3 py-2.5 text-center sm:min-w-[90px] sm:flex-1 ${
              animal.next_feed && animal.next_feed.days_until < 0
                ? 'border-sand'
                : animal.next_feed && animal.next_feed.days_until <= 2
                  ? 'border-olive'
                  : 'border-border-hi'
            }`}
          >
            <div
              className={`font-display text-[18px] font-bold leading-none ${
                animal.next_feed && animal.next_feed.days_until < 0 ? 'text-bone' : 'text-sand'
              }`}
            >
              {animal.next_feed?.due_date?.slice(5) || '—'}
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Next feed</div>
            <div
              className={`mt-1 font-display text-[18px] font-bold leading-none ${
                animal.next_feed && animal.next_feed.days_until < 0 ? 'text-bone' : 'text-sand'
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
            className={`min-w-0 rounded-[10px] border bg-bark px-3 py-2.5 text-center sm:min-w-[90px] sm:flex-1 ${
              animal.next_maintenance && animal.next_maintenance.days_until < 0
                ? 'border-sand'
                : animal.next_maintenance && animal.next_maintenance.days_until <= 1
                  ? 'border-olive'
                  : 'border-border-hi'
            }`}
          >
            <div
              className={`font-display text-[18px] font-bold leading-none ${
                animal.next_maintenance && animal.next_maintenance.days_until < 0
                  ? 'text-bone'
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
            className={`min-w-0 rounded-[10px] border bg-bark px-3 py-2.5 text-center sm:min-w-[90px] sm:flex-1 ${
              animal.handling_gap.overdue ? 'border-olive' : 'border-border-hi'
            }`}
          >
            <div className="font-display text-[18px] font-bold leading-none text-sand">
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
          <div className="min-w-0 rounded-[10px] border border-border-hi bg-bark px-3 py-2.5 text-center sm:min-w-[90px] sm:flex-1">
            <div className="font-display text-[18px] font-bold leading-none text-sand">
              {animal.last_shed?.date?.slice(5) || '—'}
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.1em] text-muted">Last shed</div>
            <div className="mt-0.5 text-[10px] text-muted">{animal.last_shed?.quality || 'None logged'}</div>
          </div>
        </div>
        <div className="mt-2.5">
          <span className="inline-block rounded-full border border-sand bg-bark px-3 py-1 font-mono text-[11px] text-sand">
            {animal.stage.label} · {animal.stage.desc}
          </span>
        </div>
      </header>

      <nav className="sticky top-0 z-10 flex gap-0 overflow-x-auto border-b border-border bg-charcoal scrollbar-none [-webkit-overflow-scrolling:touch]">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`min-h-11 shrink-0 whitespace-nowrap border-b-2 px-3.5 py-3 text-[11px] font-bold uppercase tracking-[0.08em] transition sm:px-4 sm:py-2.5 sm:text-xs ${
              tab === t.id
                ? 'border-sand text-sand'
                : 'border-transparent text-muted hover:text-bone-dark'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="px-4 pb-8 pt-4 sm:px-6 sm:pb-7 sm:pt-5">
        {tab === 'overview' && <OverviewTab animal={animal} feeds={feeds} onChange={refresh} />}
        {tab === 'logs' && <LogsTab animal={animal} onChange={refresh} />}
        {tab === 'stats' && <StatsTab animal={animal} onChange={refresh} />}
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
