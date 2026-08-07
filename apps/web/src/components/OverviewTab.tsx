import { useState } from 'react'
import {
  api,
  todayStr,
  type AnimalOverview,
  type Feed,
} from '../api/client'
import { Btn, BtnSm, Card, CardTitle, Empty, Field, Input, LogForm, SectionLabel, Select } from './ui'

const PREY = [
  'Pinky mouse',
  'Fuzzy mouse',
  'Adult mouse',
  'Small rat',
  'Medium rat',
  'Large rat',
  'Day-old chick',
  'Quail',
  'Rabbit',
]

export function OverviewTab({
  animal,
  feeds,
  onChange,
}: {
  animal: AnimalOverview
  feeds: Feed[]
  onChange: () => void
}) {
  const [date, setDate] = useState(todayStr())
  const [prey, setPrey] = useState('Adult mouse')
  const [accepted, setAccepted] = useState(true)
  const [preyWeight, setPreyWeight] = useState('')
  const [snakeWeight, setSnakeWeight] = useState('')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)

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

  return (
    <div>
      {animal.reminders.length > 0 && (
        <>
          <SectionLabel>Reminders</SectionLabel>
          <div className="mb-3 flex flex-col gap-2">
            {animal.reminders.map((r) => (
              <div
                key={r.kind + r.message}
                className={`rounded-lg border px-3 py-2 text-[13px] ${
                  r.severity === 'high'
                    ? 'border-[#E06050] bg-[#3a1510] text-[#E08070]'
                    : r.severity === 'medium'
                      ? 'border-[#D4A040] bg-[#3a2a10] text-[#E8C080]'
                      : 'border-border-hi bg-charcoal text-bone-dark'
                }`}
              >
                {r.message}
              </div>
            ))}
          </div>
        </>
      )}

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
        <div className="mt-3 rounded-lg border border-sand bg-[#4a2c14] px-3 py-2 text-[13px] text-sand">
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
              {PREY.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </Select>
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
              <tr key={f.id} className="border-b border-[#3a2415] text-[12px] text-bone-dark">
                <td className="px-2.5 py-2 font-mono text-[11px]">{f.date}</td>
                <td className="px-2.5 py-2">{f.prey_type}</td>
                <td className="px-2.5 py-2">{f.prey_weight_g != null ? `${f.prey_weight_g}g` : '—'}</td>
                <td className={`px-2.5 py-2 font-bold ${f.accepted ? 'text-sage' : 'text-[#E06050]'}`}>
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
