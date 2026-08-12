import { useMemo, useState } from 'react'
import {
  api,
  todayStr,
  type AnimalOverview,
  type Feed,
  type PreyStatus,
  type Reminder,
} from '../api/client'
import { Btn, BtnSm, Card, CardTitle, Empty, Field, Input, LogForm, SectionLabel, Select } from './ui'

const STATUS_LABEL: Record<PreyStatus, string> = {
  recommended: 'Recommended',
  acceptable: 'Acceptable',
  alternative: 'Alternative',
  too_small: 'Too small',
  too_large: 'Too large',
  unknown: 'Unknown',
}

const STATUS_CLASS: Record<PreyStatus, string> = {
  recommended: 'text-sage',
  acceptable: 'text-sand',
  alternative: 'text-bone-dark',
  too_small: 'text-muted',
  too_large: 'text-bone',
  unknown: 'text-muted',
}

type DueGroupId = 'weight' | 'feeding' | 'handling' | 'shed' | 'habitat' | 'maintenance'

const DUE_GROUP_ORDER: { id: DueGroupId; label: string }[] = [
  { id: 'weight', label: 'Weight' },
  { id: 'feeding', label: 'Feeding' },
  { id: 'handling', label: 'Handling' },
  { id: 'shed', label: 'Shed' },
  { id: 'habitat', label: 'Habitat' },
  { id: 'maintenance', label: 'Maintenance' },
]

function reminderGroup(kind: string): DueGroupId | null {
  if (kind === 'handle_wait') return null
  if (kind.startsWith('weight')) return 'weight'
  if (kind.startsWith('feed_')) return 'feeding'
  if (kind.startsWith('handling')) return 'handling'
  if (kind.startsWith('shed')) return 'shed'
  if (kind.startsWith('env_')) return 'habitat'
  if (kind.startsWith('maint')) return 'maintenance'
  return null
}

function groupedDueReminders(reminders: Reminder[]) {
  const buckets = new Map<DueGroupId, Reminder[]>()
  const other: Reminder[] = []
  for (const r of reminders) {
    const g = reminderGroup(r.kind)
    if (!g) {
      if (r.kind !== 'handle_wait') other.push(r)
      continue
    }
    const list = buckets.get(g) ?? []
    list.push(r)
    buckets.set(g, list)
  }
  return {
    groups: DUE_GROUP_ORDER.filter((g) => buckets.has(g.id)).map((g) => ({
      ...g,
      items: buckets.get(g.id) ?? [],
    })),
    other,
  }
}

export function OverviewTab({
  animal,
  feeds,
  onChange,
}: {
  animal: AnimalOverview
  feeds: Feed[]
  onChange: () => void
}) {
  const preyList = animal.prey_categories
  const defaultPrey =
    animal.feeding_recommendation.suggested_prey ??
    animal.feeding_recommendation.recommended_prey[0] ??
    preyList[0] ??
    'Adult mouse'

  const [date, setDate] = useState(todayStr())
  const [prey, setPrey] = useState(defaultPrey)
  const [accepted, setAccepted] = useState(true)
  const [preyWeight, setPreyWeight] = useState('')
  const [snakeWeight, setSnakeWeight] = useState('')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)

  const liveStatus: PreyStatus | null = useMemo(() => {
    return animal.feeding_recommendation.prey_status_by_category[prey] ?? 'unknown'
  }, [animal.feeding_recommendation.prey_status_by_category, prey])

  async function logFeed() {
    setBusy(true)
    try {
      await api.feeds.create({
        date,
        prey_type: prey,
        accepted,
        prey_weight_g: preyWeight ? Number(preyWeight) : null,
        snake_weight_g: snakeWeight ? Number(snakeWeight) : null,
        notes,
      })
      setNotes('')
      setPreyWeight('')
      setSnakeWeight('')
      onChange()
    } finally {
      setBusy(false)
    }
  }

  const next = animal.next_feed
  const fr = animal.feeding_recommendation
  const iv = fr.feeding_interval
  const due = groupedDueReminders(animal.reminders)

  return (
    <div>
      <div className="mb-4 grid gap-6 sm:grid-cols-2">
        <section aria-label="Due soon">
          <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-muted">
            Due soon
          </div>
          {due.groups.length === 0 && due.other.length === 0 ? (
            <p className="text-[13px] text-muted">Nothing due</p>
          ) : (
            <div className="space-y-3">
              {due.groups.map((g) => (
                <div key={g.id}>
                  <div className="font-mono text-[10px] font-bold uppercase tracking-[0.1em] text-sand">
                    {g.label}
                  </div>
                  <ul className="mt-1 space-y-1.5">
                    {g.items.map((r) => (
                      <li key={r.kind + r.message}>
                        <div
                          className={`text-[13px] leading-snug ${
                            r.severity === 'high' ? 'font-semibold text-bone' : 'text-bone'
                          }`}
                        >
                          {r.message}
                        </div>
                        {r.why ? <div className="mt-0.5 text-[11px] text-muted">{r.why}</div> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {due.other.length > 0 && (
                <ul className="space-y-1.5">
                  {due.other.map((r) => (
                    <li key={r.kind + r.message}>
                      <div className="text-[13px] leading-snug text-bone">{r.message}</div>
                      {r.why ? <div className="mt-0.5 text-[11px] text-muted">{r.why}</div> : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>

        <section aria-label="Feeding recommendation">
          <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-muted">
            Feeding · {fr.stage}
          </div>
          <ul className="list-disc space-y-1.5 pl-4 text-[13px] leading-snug text-bone-dark">
            <li>
              Every {next?.interval_days ?? iv.recommended_days}d
              <span className="text-muted">
                {' '}
                · safe {iv.min_days}–{iv.max_days}d
                {next?.interval_source ? ` · ${next.interval_source}` : ''}
              </span>
            </li>
            <li>
              Handle {animal.clear_to_handle.clear_after_hours}h after feed. Overdue feeds don&apos;t
              stretch the next gap.
            </li>
            {next?.interval_why ? <li className="text-muted">{next.interval_why}</li> : null}
            <li>
              Suggested: {fr.suggested_prey ?? fr.recommended_prey[0] ?? '—'}
              {fr.suggestion_why ? ` — ${fr.suggestion_why}` : ''}
            </li>
            <li>Stage band: {fr.recommended_prey.join(', ')}</li>
            {animal.last_feed && fr.prey_status ? (
              <li className={STATUS_CLASS[fr.prey_status]}>
                Last prey ({animal.last_feed.prey_type}): {STATUS_LABEL[fr.prey_status]}
              </li>
            ) : null}
            {animal.shed_prediction?.estimate_date ? (
              <li className="text-muted">
                Next shed ~{animal.shed_prediction.estimate_date}
                {animal.shed_prediction.median_days != null
                  ? ` (median ${animal.shed_prediction.median_days}d)`
                  : ''}
              </li>
            ) : null}
          </ul>
        </section>
      </div>

      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        <Card>
          <CardTitle>Last Fed</CardTitle>
          <div className="font-display text-[22px] font-semibold text-bone">
            {animal.last_feed?.date || '—'}
          </div>
          <div className="mt-1 text-xs text-muted">
            {animal.last_feed ? animal.last_feed.prey_type : 'No feeds logged'}
            {next ? ` · next ${next.due_date}` : ''}
          </div>
        </Card>
        <Card>
          <CardTitle>Current Weight</CardTitle>
          <div className="font-display text-[22px] font-semibold text-bone">
            {animal.current_weight_g != null ? `${animal.current_weight_g}g` : '—'}
          </div>
          <div className="mt-1 text-xs text-muted">{animal.current_weight_date || 'Not logged'}</div>
        </Card>
        <Card>
          <CardTitle>Last Shed</CardTitle>
          <div className="font-display text-[22px] font-semibold text-bone">
            {animal.last_shed?.date || '—'}
          </div>
          <div className="mt-1 text-xs text-muted">{animal.last_shed?.quality || 'No sheds logged'}</div>
        </Card>
      </div>

      {animal.shed_mode.active && (
        <div className="mt-3 rounded-lg border border-sand bg-bark px-3 py-2 text-[13px] text-sand">
          Shed status: {animal.shed_mode.status} · humidity {animal.shed_mode.humidity_target}
          {animal.shed_mode.dont_feed ? ' · do not feed while opaque' : ''}
        </div>
      )}

      <SectionLabel>Quick feed log</SectionLabel>
      <LogForm title="Log a Feed">
        <div className="mb-2.5 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          <Field label="Prey Type">
            <Select value={prey} onChange={(e) => setPrey(e.target.value)}>
              {preyList.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
            {liveStatus && (
              <div className={`mt-1 text-[11px] ${STATUS_CLASS[liveStatus]}`}>
                {STATUS_LABEL[liveStatus]} for {fr.stage}
              </div>
            )}
          </Field>
          <Field label="Accepted?">
            <Select
              value={accepted ? 'yes' : 'no'}
              onChange={(e) => setAccepted(e.target.value === 'yes')}
            >
              <option value="yes">Yes</option>
              <option value="no">Refused</option>
            </Select>
          </Field>
          <Field label="Prey (g)" className="max-w-[100px]">
            <Input
              type="number"
              placeholder="e.g. 25"
              value={preyWeight}
              onChange={(e) => setPreyWeight(e.target.value)}
            />
          </Field>
          <Field label="Weight (g)" className="max-w-[100px]">
            <Input
              type="number"
              placeholder="e.g. 320"
              value={snakeWeight}
              onChange={(e) => setSnakeWeight(e.target.value)}
            />
          </Field>
        </div>
        <div className="flex items-center gap-2.5">
          <Input
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="flex-1"
          />
          <Btn onClick={logFeed} disabled={busy}>
            Log Feed
          </Btn>
        </div>
      </LogForm>

      <SectionLabel>Recent feeding history</SectionLabel>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border text-left font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
            <th className="px-2.5 py-1.5">Date</th>
            <th className="px-2.5 py-1.5">Prey</th>
            <th className="px-2.5 py-1.5">Prey g</th>
            <th className="px-2.5 py-1.5">Result</th>
            <th className="px-2.5 py-1.5">Weight</th>
            <th className="px-2.5 py-1.5">Notes</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {feeds.length === 0 ? (
            <tr>
              <td colSpan={7}>
                <Empty>No feeds logged yet.</Empty>
              </td>
            </tr>
          ) : (
            feeds.map((f) => (
              <tr key={f.id} className="border-b border-border text-[12px] text-bone-dark">
                <td className="px-2.5 py-2 font-mono text-[11px]">{f.date}</td>
                <td className="px-2.5 py-2">{f.prey_type}</td>
                <td className="px-2.5 py-2">{f.prey_weight_g != null ? `${f.prey_weight_g}g` : '—'}</td>
                <td className={`px-2.5 py-2 font-bold ${f.accepted ? 'text-sage' : 'text-bone'}`}>
                  {f.accepted ? '✓ Accepted' : '✗ Refused'}
                </td>
                <td className="px-2.5 py-2">{f.snake_weight_g != null ? `${f.snake_weight_g}g` : '—'}</td>
                <td className="px-2.5 py-2 text-[11px] text-muted">{f.notes || '—'}</td>
                <td className="px-2.5 py-2">
                  <BtnSm
                    onClick={async () => {
                      await api.feeds.remove(f.id)
                      onChange()
                    }}
                  >
                    ✕
                  </BtnSm>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
