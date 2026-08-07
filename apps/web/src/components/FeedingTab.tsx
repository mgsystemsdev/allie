import { useEffect, useState } from 'react'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, todayStr, type AnimalOverview, type Weight, type Regurg } from '../api/client'
import { Btn, BtnSm, Card, Empty, Field, Input, LogForm, SectionLabel, Select } from './ui'

const STAGE_ORDER = ['Hatchling', 'Juvenile', 'Sub-adult', 'Adult'] as const

export function FeedingTab({
  animal,
  onChange,
}: {
  animal: AnimalOverview
  onChange: () => void
}) {
  const [weights, setWeights] = useState<Weight[]>([])
  const [regurgs, setRegurgs] = useState<Regurg[]>([])
  const [wDate, setWDate] = useState(todayStr())
  const [wVal, setWVal] = useState('')
  const [rDate, setRDate] = useState(todayStr())
  const [rSeverity, setRSeverity] = useState('moderate')
  const [rNotes, setRNotes] = useState('')

  async function load() {
    const [w, r] = await Promise.all([api.weights.list(), api.regurgitations.list()])
    setWeights(w)
    setRegurgs(r)
  }

  useEffect(() => {
    void load()
  }, [])

  const stages = animal.feeding_stages
  const current = animal.stage.label

  return (
    <div>
      <SectionLabel>Feeding frequency by life stage</SectionLabel>
      <Card className="mb-3">
        {STAGE_ORDER.map((label) => {
          const rules = stages[label]
          if (!rules) return null
          const iv = rules.feeding_interval
          const cur = label === current
          const widthPct = Math.round((100 * (22 - iv.recommended_days)) / 16)
          return (
            <div
              key={label}
              className={`flex items-center justify-between border-b border-border py-2 text-[13px] last:border-0 ${cur ? 'rounded-md bg-[rgba(196,148,106,0.08)] px-2' : ''}`}
            >
              <span className={cur ? 'text-sand' : 'text-muted'}>
                {cur ? `★ ${label}` : label} ({rules.desc})
              </span>
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-28 overflow-hidden rounded bg-charcoal">
                  <div
                    className="h-full rounded bg-sand"
                    style={{ width: `${Math.max(25, Math.min(100, widthPct))}%` }}
                  />
                </div>
                <span className="min-w-[90px] text-right font-mono text-[11px] text-sand">
                  Every {iv.min_days}–{iv.max_days}d
                </span>
              </div>
            </div>
          )
        })}
      </Card>

      <SectionLabel>Weight log</SectionLabel>
      <LogForm title="Log Weight">
        <div className="flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={wDate} onChange={(e) => setWDate(e.target.value)} />
          </Field>
          <Field label="Weight (g)">
            <Input type="number" value={wVal} onChange={(e) => setWVal(e.target.value)} placeholder="e.g. 180" />
          </Field>
          <div className="flex items-end pb-0.5">
            <Btn
              onClick={async () => {
                if (!wVal) return
                await api.weights.create({ date: wDate, weight_g: Number(wVal) })
                setWVal('')
                await load()
                onChange()
              }}
            >
              Save
            </Btn>
          </div>
        </div>
      </LogForm>

      <div className="mb-4 h-[180px] w-full">
        {weights.length === 0 ? (
          <Empty>Weight chart — no data yet.</Empty>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={weights.map((w) => ({ date: w.date, weight: w.weight_g }))}>
              <XAxis dataKey="date" stroke="#9C8068" tick={{ fontSize: 11 }} />
              <YAxis stroke="#9C8068" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#2C201A', border: '1px solid #5a3a22', color: '#F2E8D9' }}
              />
              <Line type="monotone" dataKey="weight" stroke="#C4946A" strokeWidth={2} dot={{ fill: '#C4946A' }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <SectionLabel>Weight history</SectionLabel>
      {weights.length === 0 ? (
        <Empty>No weights logged.</Empty>
      ) : (
        <ul className="mb-4 space-y-2">
          {[...weights].reverse().map((w) => (
            <li
              key={w.id}
              className="flex items-center justify-between rounded-lg border border-border bg-[#2a1a10] px-3 py-2 text-[13px]"
            >
              <div className="font-bold text-bone">
                {w.date} · {w.weight_g}g
              </div>
              <BtnSm
                onClick={async () => {
                  await api.weights.remove(w.id)
                  await load()
                  onChange()
                }}
              >
                ✕
              </BtnSm>
            </li>
          ))}
        </ul>
      )}

      <SectionLabel>Regurgitation log</SectionLabel>
      <p className="mb-2 text-[12px] text-muted">
        Separate from refusal — regurgitation is a health red flag.
      </p>
      <LogForm title="Log Regurgitation">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={rDate} onChange={(e) => setRDate(e.target.value)} />
          </Field>
          <Field label="Severity">
            <Select value={rSeverity} onChange={(e) => setRSeverity(e.target.value)}>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </Select>
          </Field>
          <Field label="Notes">
            <Input value={rNotes} onChange={(e) => setRNotes(e.target.value)} placeholder="Details..." />
          </Field>
        </div>
        <Btn
          onClick={async () => {
            await api.regurgitations.create({ date: rDate, severity: rSeverity, notes: rNotes })
            setRNotes('')
            await load()
          }}
        >
          Log Regurg
        </Btn>
      </LogForm>
      {regurgs.length === 0 ? (
        <Empty>No regurgitations logged.</Empty>
      ) : (
        <ul className="space-y-2">
          {regurgs.map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between rounded-lg border border-[#E06050]/40 bg-[#3a1510] px-3 py-2 text-[13px]"
            >
              <div>
                <div className="font-bold text-[#E08070]">
                  {r.date} · {r.severity}
                </div>
                <div className="text-muted">{r.notes || '—'}</div>
              </div>
              <BtnSm
                onClick={async () => {
                  await api.regurgitations.remove(r.id)
                  await load()
                }}
              >
                ✕
              </BtnSm>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
