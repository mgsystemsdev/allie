import { useEffect, useState } from 'react'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, todayStr, type Regurg, type Weight } from '../api/client'
import { Btn, BtnSm, Card, Empty, Field, Input, LogForm, SectionLabel, Select } from './ui'

export function FeedingTab({ onChange }: { onChange: () => void }) {
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

  return (
    <div>
      <SectionLabel>Feeding frequency by life stage</SectionLabel>
      <Card className="mb-3">
        {[
          ['Hatchling (0–3 mo)', '100%', 'Every 5–7d'],
          ['★ Juvenile (3–12 mo) — Allie', '75%', 'Every 7–10d', true],
          ['Sub-adult (1–3 yr)', '55%', 'Every 10–14d'],
          ['Adult (3+ yr)', '35%', 'Every 14–21d'],
        ].map(([label, width, freq, cur]) => (
          <div
            key={String(label)}
            className={`flex items-center justify-between border-b border-border py-2 text-[13px] last:border-0 ${cur ? 'rounded-md bg-[rgba(196,148,106,0.08)] px-2' : ''}`}
          >
            <span className={cur ? 'text-sand' : 'text-muted'}>{label}</span>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-28 overflow-hidden rounded bg-charcoal">
                <div className="h-full rounded bg-sand" style={{ width: String(width) }} />
              </div>
              <span className="min-w-[70px] text-right font-mono text-[11px] text-sand">{freq}</span>
            </div>
          </div>
        ))}
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
