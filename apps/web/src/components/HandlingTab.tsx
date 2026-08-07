import { useEffect, useState } from 'react'
import { api, todayStr, type AnimalOverview, type Handling } from '../api/client'
import { Btn, BtnSm, Empty, Field, Input, LogForm, SectionLabel, Select } from './ui'

export function HandlingTab({ animal, onChange }: { animal: AnimalOverview; onChange: () => void }) {
  const [rows, setRows] = useState<Handling[]>([])
  const [date, setDate] = useState(todayStr())
  const [duration, setDuration] = useState('15')
  const [temp, setTemp] = useState('calm')
  const [notes, setNotes] = useState('')

  async function load() {
    setRows(await api.handlings.list())
  }

  useEffect(() => {
    void load()
  }, [])

  const blocked = !animal.clear_to_handle.ready

  return (
    <div>
      <div
        className={`mb-4 rounded-lg border px-3 py-2 text-[13px] ${
          blocked ? 'border-[#D4A040] bg-[#3a2a10] text-[#E8C080]' : 'border-olive bg-[#1a3a20] text-sage'
        }`}
      >
        {animal.clear_to_handle.message}
      </div>

      <SectionLabel>Log handling</SectionLabel>
      <LogForm title="Handling Session">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          <Field label="Duration (min)">
            <Input type="number" value={duration} onChange={(e) => setDuration(e.target.value)} />
          </Field>
          <Field label="Temperament">
            <Select value={temp} onChange={(e) => setTemp(e.target.value)}>
              <option value="calm">Calm</option>
              <option value="nippy">Nippy</option>
              <option value="musk">Musk</option>
            </Select>
          </Field>
          <Field label="Notes">
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </div>
        <Btn
          disabled={blocked}
          onClick={async () => {
            await api.handlings.create({
              date,
              duration_min: Number(duration) || 15,
              temperament: temp,
              notes,
            })
            setNotes('')
            await load()
            onChange()
          }}
        >
          {blocked ? 'Blocked — wait after feed' : 'Log Handling'}
        </Btn>
      </LogForm>

      <SectionLabel>History</SectionLabel>
      {rows.length === 0 ? (
        <Empty>No handling sessions logged.</Empty>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-border text-left font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
              <th className="px-2.5 py-1.5">Date</th>
              <th className="px-2.5 py-1.5">Duration</th>
              <th className="px-2.5 py-1.5">Temperament</th>
              <th className="px-2.5 py-1.5">Notes</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[#3a2415] text-[12px] text-bone-dark">
                <td className="px-2.5 py-2 font-mono text-[11px]">{r.date}</td>
                <td className="px-2.5 py-2">{r.duration_min} min</td>
                <td className="px-2.5 py-2 capitalize text-sand">{r.temperament}</td>
                <td className="px-2.5 py-2 text-muted">{r.notes || '—'}</td>
                <td className="px-2.5 py-2">
                  <BtnSm
                    onClick={async () => {
                      await api.handlings.remove(r.id)
                      await load()
                    }}
                  >
                    ✕
                  </BtnSm>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
