import { useEffect, useState } from 'react'
import {
  api,
  todayStr,
  type Contact,
  type Elimination,
  type ShedCycle,
  type Treatment,
  type VetVisit,
} from '../api/client'
import { Btn, BtnSm, Card, Field, Input, LogForm, SectionLabel, Select } from './ui'

export function HealthTab({ onChange }: { onChange: () => void }) {
  const [sheds, setSheds] = useState<ShedCycle[]>([])
  const [elims, setElims] = useState<Elimination[]>([])
  const [vets, setVets] = useState<VetVisit[]>([])
  const [treatments, setTreatments] = useState<Treatment[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])

  const [shedStatus, setShedStatus] = useState('blue')
  const [shedStart, setShedStart] = useState(todayStr())
  const [shedQuality, setShedQuality] = useState('Complete (one piece)')
  const [shedEyes, setShedEyes] = useState('Yes')

  const [eDate, setEDate] = useState(todayStr())
  const [eKind, setEKind] = useState('both')
  const [eNotes, setENotes] = useState('')

  const [vDate, setVDate] = useState(todayStr())
  const [vReason, setVReason] = useState('')
  const [vNotes, setVNotes] = useState('')

  const [tStart, setTStart] = useState(todayStr())
  const [tName, setTName] = useState('')
  const [tReason, setTReason] = useState('')

  const [cLabel, setCLabel] = useState('')
  const [cPhone, setCPhone] = useState('')
  const [cClinic, setCClinic] = useState('')
  const [cEmergency, setCEmergency] = useState(false)

  async function load() {
    const [s, e, v, t, c] = await Promise.all([
      api.shedCycles.list(),
      api.eliminations.list(),
      api.vetVisits.list(),
      api.treatments.list(),
      api.contacts.list(),
    ])
    setSheds(s)
    setElims(e)
    setVets(v)
    setTreatments(t)
    setContacts(c)
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div>
      <SectionLabel>Shed cycle</SectionLabel>
      <LogForm title="Update Shed Status">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Status">
            <Select value={shedStatus} onChange={(e) => setShedStatus(e.target.value)}>
              <option value="clear">Clear</option>
              <option value="blue">Blue eyes</option>
              <option value="opaque">Opaque</option>
              <option value="shed">Shed complete</option>
            </Select>
          </Field>
          <Field label="Started">
            <Input type="date" value={shedStart} onChange={(e) => setShedStart(e.target.value)} />
          </Field>
          <Field label="Quality (if shed)">
            <Select value={shedQuality} onChange={(e) => setShedQuality(e.target.value)}>
              <option>Complete (one piece)</option>
              <option>Partial (some retained)</option>
              <option>Poor (multiple pieces)</option>
            </Select>
          </Field>
          <Field label="Eyes clear pre-shed?">
            <Select value={shedEyes} onChange={(e) => setShedEyes(e.target.value)}>
              <option>Yes</option>
              <option>No — retained eye caps</option>
            </Select>
          </Field>
        </div>
        <Btn
          onClick={async () => {
            await api.shedCycles.create({
              status: shedStatus,
              started_at: shedStart,
              completed_at: shedStatus === 'shed' ? shedStart : null,
              quality: shedStatus === 'shed' ? shedQuality : null,
              eyes: shedEyes,
            })
            await load()
            onChange()
          }}
        >
          Log Shed Status
        </Btn>
      </LogForm>
      <div className="mb-4 space-y-2">
        {sheds.map((s) => (
          <div key={s.id} className="flex items-center gap-3 rounded-[10px] border border-border bg-charcoal p-3.5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 border-olive bg-bark text-xl">
              🐍
            </div>
            <div className="flex-1">
              <div className="text-[13px] font-bold text-bone">
                {s.started_at} · <span className="text-sand">{s.status}</span>
              </div>
              <div className="mt-0.5 text-[12px] text-muted">
                {s.quality || '—'} · Eyes: {s.eyes || '—'}
              </div>
            </div>
            <BtnSm
              onClick={async () => {
                await api.shedCycles.remove(s.id)
                await load()
                onChange()
              }}
            >
              ✕
            </BtnSm>
          </div>
        ))}
      </div>

      <SectionLabel>Poop / urates</SectionLabel>
      <LogForm title="Elimination Log">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={eDate} onChange={(e) => setEDate(e.target.value)} />
          </Field>
          <Field label="Kind">
            <Select value={eKind} onChange={(e) => setEKind(e.target.value)}>
              <option value="feces">Feces</option>
              <option value="urates">Urates</option>
              <option value="both">Both</option>
            </Select>
          </Field>
          <Field label="Notes">
            <Input value={eNotes} onChange={(e) => setENotes(e.target.value)} />
          </Field>
        </div>
        <Btn
          onClick={async () => {
            await api.eliminations.create({ date: eDate, kind: eKind, notes: eNotes })
            setENotes('')
            await load()
          }}
        >
          Log
        </Btn>
      </LogForm>
      {elims.length === 0 ? (
        <div className="mb-3 p-4 text-center text-[13px] text-muted">No eliminations logged.</div>
      ) : (
        <ul className="mb-4 space-y-1">
          {elims.map((e) => (
            <li key={e.id} className="flex justify-between text-[13px] text-bone-dark">
              <span>
                {e.date} · {e.kind} {e.notes ? `— ${e.notes}` : ''}
              </span>
              <BtnSm
                onClick={async () => {
                  await api.eliminations.remove(e.id)
                  await load()
                }}
              >
                ✕
              </BtnSm>
            </li>
          ))}
        </ul>
      )}

      <SectionLabel>Treatments / meds</SectionLabel>
      <LogForm title="Log Treatment">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Started">
            <Input type="date" value={tStart} onChange={(e) => setTStart(e.target.value)} />
          </Field>
          <Field label="Name">
            <Input value={tName} onChange={(e) => setTName(e.target.value)} placeholder="e.g. mite treatment" />
          </Field>
          <Field label="Reason">
            <Input value={tReason} onChange={(e) => setTReason(e.target.value)} />
          </Field>
        </div>
        <Btn
          onClick={async () => {
            if (!tName) return
            await api.treatments.create({ started_at: tStart, name: tName, reason: tReason })
            setTName('')
            setTReason('')
            await load()
          }}
        >
          Save Treatment
        </Btn>
      </LogForm>
      {treatments.map((t) => (
        <div key={t.id} className="mb-1 flex justify-between text-[13px] text-bone-dark">
          <span>
            {t.started_at} · {t.name} {t.reason ? `(${t.reason})` : ''}
          </span>
          <BtnSm
            onClick={async () => {
              await api.treatments.remove(t.id)
              await load()
            }}
          >
            ✕
          </BtnSm>
        </div>
      ))}

      <SectionLabel>Vet visits</SectionLabel>
      <LogForm title="Log Vet Visit">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={vDate} onChange={(e) => setVDate(e.target.value)} />
          </Field>
          <Field label="Reason">
            <Input value={vReason} onChange={(e) => setVReason(e.target.value)} placeholder="Annual check..." />
          </Field>
          <Field label="Notes">
            <Input value={vNotes} onChange={(e) => setVNotes(e.target.value)} />
          </Field>
        </div>
        <Btn
          onClick={async () => {
            if (!vReason) return
            await api.vetVisits.create({ date: vDate, reason: vReason, notes: vNotes })
            setVReason('')
            setVNotes('')
            await load()
          }}
        >
          Save
        </Btn>
      </LogForm>
      {vets.length === 0 ? (
        <div className="mb-3 p-4 text-center text-[13px] text-muted">No vet visits logged.</div>
      ) : (
        <table className="mb-4 w-full text-[12px]">
          <tbody>
            {vets.map((v) => (
              <tr key={v.id} className="border-b border-border text-bone-dark">
                <td className="px-2 py-2 font-mono">{v.date}</td>
                <td className="px-2 py-2">{v.reason}</td>
                <td className="px-2 py-2 text-muted">{v.notes || '—'}</td>
                <td className="px-2 py-2">
                  <BtnSm
                    onClick={async () => {
                      await api.vetVisits.remove(v.id)
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

      <SectionLabel>Vet / emergency contacts</SectionLabel>
      <LogForm title="Add Contact">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Label">
            <Input value={cLabel} onChange={(e) => setCLabel(e.target.value)} placeholder="Exotic vet" />
          </Field>
          <Field label="Phone">
            <Input value={cPhone} onChange={(e) => setCPhone(e.target.value)} />
          </Field>
          <Field label="Clinic">
            <Input value={cClinic} onChange={(e) => setCClinic(e.target.value)} />
          </Field>
          <Field label="Emergency?">
            <Select
              value={cEmergency ? 'yes' : 'no'}
              onChange={(e) => setCEmergency(e.target.value === 'yes')}
            >
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </Select>
          </Field>
        </div>
        <Btn
          onClick={async () => {
            if (!cLabel) return
            await api.contacts.create({
              label: cLabel,
              phone: cPhone,
              clinic: cClinic,
              is_emergency: cEmergency,
            })
            setCLabel('')
            setCPhone('')
            setCClinic('')
            await load()
          }}
        >
          Add Contact
        </Btn>
      </LogForm>
      {contacts.map((c) => (
        <Card key={c.id} className="mb-2 flex justify-between">
          <div>
            <div className="text-[13px] font-bold text-bone">
              {c.label} {c.is_emergency ? <span className="text-bone">· Emergency</span> : null}
            </div>
            <div className="text-[12px] text-muted">
              {c.phone} {c.clinic ? `· ${c.clinic}` : ''}
            </div>
          </div>
          <BtnSm
            onClick={async () => {
              await api.contacts.remove(c.id)
              await load()
            }}
          >
            ✕
          </BtnSm>
        </Card>
      ))}

      <SectionLabel>Health indicators (reference)</SectionLabel>
      <div className="mt-2.5 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {[
          ['good', 'Clear, alert eyes', 'Eyes — positive sign'],
          ['good', 'Clean vent, no swelling', 'Cloaca — check monthly'],
          ['good', 'Firm, rounded muscle tone', 'Body condition'],
          ['warn', 'Wheezing / mucus', 'Respiratory — see vet'],
          ['warn', 'Retained shed / eye caps', 'Raise humidity, add damp hide'],
          ['bad', 'Repeated regurgitation', 'Parasites / temps off — vet'],
          ['bad', 'Stargazing / wobbling', 'Neurological — vet urgently'],
          ['bad', 'Mites — tiny black dots', 'Treat enclosure + snake'],
        ].map(([dot, text, label]) => (
          <div key={text} className="flex items-center gap-2.5 rounded-lg border border-border bg-charcoal p-3">
            <div
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                dot === 'good' ? 'bg-sage' : dot === 'warn' ? 'bg-ochre' : 'bg-deep-red'
              }`}
            />
            <div>
              <div className="text-[12px] text-bone-dark">{text}</div>
              <div className="text-[10px] text-muted">{label}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
