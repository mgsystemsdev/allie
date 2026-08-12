import { useEffect, useMemo, useState } from 'react'
import { api, todayStr, type AnimalOverview, type PreyStatus } from '../api/client'
import { Btn, Field, Input, LogForm, Select } from './ui'

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

export function LogsTab({ animal, onChange }: { animal: AnimalOverview; onChange: () => void }) {
  const preyList = animal.prey_categories
  const fr = animal.feeding_recommendation
  const defaultPrey =
    fr.suggested_prey ?? fr.recommended_prey[0] ?? preyList[0] ?? 'Adult mouse'
  const blocked = !animal.clear_to_handle.ready

  const [busy, setBusy] = useState('')
  const [feedDate, setFeedDate] = useState(todayStr())
  const [prey, setPrey] = useState(defaultPrey)
  const [accepted, setAccepted] = useState(true)
  const [preyWeight, setPreyWeight] = useState('')
  const [snakeWeight, setSnakeWeight] = useState('')
  const [feedNotes, setFeedNotes] = useState('')
  const [wDate, setWDate] = useState(todayStr())
  const [wVal, setWVal] = useState('')
  const [hDate, setHDate] = useState(todayStr())
  const [hDur, setHDur] = useState('15')
  const [hTemp, setHTemp] = useState('calm')
  const [hNotes, setHNotes] = useState('')
  const [eDate, setEDate] = useState(todayStr())
  const [eKind, setEKind] = useState('both')
  const [eNotes, setENotes] = useState('')
  const [shedStatus, setShedStatus] = useState('clear')
  const [shedStart, setShedStart] = useState(todayStr())
  const [shedQuality, setShedQuality] = useState('Complete (one piece)')
  const [shedEyes, setShedEyes] = useState('Yes')
  const [mDate, setMDate] = useState(todayStr())
  const [mKind, setMKind] = useState('water')
  const [mNotes, setMNotes] = useState('')
  const [hot, setHot] = useState('92')
  const [cool, setCool] = useState('77')
  const [night, setNight] = useState('72')
  const [rh, setRh] = useState('50')
  const [envNotes, setEnvNotes] = useState('')
  const [photoDate, setPhotoDate] = useState(todayStr())
  const [photoKind, setPhotoKind] = useState('growth')
  const [photoCaption, setPhotoCaption] = useState('')
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [useAsHero, setUseAsHero] = useState(false)
  const [rDate, setRDate] = useState(todayStr())
  const [rSev, setRSev] = useState('moderate')
  const [rNotes, setRNotes] = useState('')

  useEffect(() => {
    setPrey(
      animal.feeding_recommendation.suggested_prey ??
        animal.feeding_recommendation.recommended_prey[0] ??
        animal.prey_categories[0] ??
        'Adult mouse',
    )
    void api.envReadings.list().then((rows) => {
      const last = rows[0]
      if (!last) return
      setHot(String(last.temp_hot_f))
      setCool(String(last.temp_cool_f))
      setNight(last.temp_night_f != null ? String(last.temp_night_f) : '72')
      setRh(String(last.humidity_pct))
    })
  }, [animal.id, animal.feeding_recommendation, animal.prey_categories])

  const preyOptions = useMemo(() => preyList, [preyList])
  const liveStatus: PreyStatus =
    fr.prey_status_by_category[prey] ?? 'unknown'

  async function run(key: string, fn: () => Promise<void>) {
    setBusy(key)
    try {
      await fn()
      onChange()
    } finally {
      setBusy('')
    }
  }

  return (
    <div>
      <LogForm title="Log a Feed">
        <div className="mb-2.5 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={feedDate} onChange={(e) => setFeedDate(e.target.value)} />
          </Field>
          <Field label="Prey Type">
            <Select value={prey} onChange={(e) => setPrey(e.target.value)}>
              {preyOptions.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
            <div className={`mt-1 text-[11px] ${STATUS_CLASS[liveStatus]}`}>
              {STATUS_LABEL[liveStatus]} for {fr.stage}
            </div>
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
            value={feedNotes}
            onChange={(e) => setFeedNotes(e.target.value)}
            className="flex-1"
          />
          <Btn
            disabled={!!busy}
            onClick={() =>
              void run('feed', async () => {
                await api.feeds.create({
                  date: feedDate,
                  prey_type: prey,
                  accepted,
                  prey_weight_g: preyWeight ? Number(preyWeight) : null,
                  snake_weight_g: snakeWeight ? Number(snakeWeight) : null,
                  notes: feedNotes,
                })
                setPreyWeight('')
                setSnakeWeight('')
                setFeedNotes('')
              })
            }
          >
            Log Feed
          </Btn>
        </div>
      </LogForm>

      <LogForm title="Log Weight">
        <div className="flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={wDate} onChange={(e) => setWDate(e.target.value)} />
          </Field>
          <Field label="Weight (g)">
            <Input
              type="number"
              value={wVal}
              onChange={(e) => setWVal(e.target.value)}
              placeholder="e.g. 180"
            />
          </Field>
          <div className="flex items-end pb-0.5">
            <Btn
              disabled={!!busy || !wVal}
              onClick={() =>
                void run('weight', async () => {
                  await api.weights.create({ date: wDate, weight_g: Number(wVal) })
                  setWVal('')
                })
              }
            >
              Save
            </Btn>
          </div>
        </div>
      </LogForm>

      <LogForm title="Handling Session">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={hDate} onChange={(e) => setHDate(e.target.value)} />
          </Field>
          <Field label="Duration (min)">
            <Input type="number" value={hDur} onChange={(e) => setHDur(e.target.value)} />
          </Field>
          <Field label="Temperament">
            <Select value={hTemp} onChange={(e) => setHTemp(e.target.value)}>
              <option value="calm">Calm</option>
              <option value="nippy">Nippy</option>
              <option value="musk">Musk</option>
            </Select>
          </Field>
          <Field label="Notes">
            <Input value={hNotes} onChange={(e) => setHNotes(e.target.value)} />
          </Field>
        </div>
        <Btn
          disabled={!!busy || blocked}
          onClick={() =>
            void run('handle', async () => {
              await api.handlings.create({
                date: hDate,
                duration_min: Number(hDur) || 15,
                temperament: hTemp,
                notes: hNotes,
              })
              setHNotes('')
            })
          }
        >
          {blocked ? 'Locked until timer clears' : 'Log Handling'}
        </Btn>
      </LogForm>

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
          disabled={!!busy}
          onClick={() =>
            void run('elim', async () => {
              await api.eliminations.create({ date: eDate, kind: eKind, notes: eNotes })
              setENotes('')
            })
          }
        >
          Log
        </Btn>
      </LogForm>

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
          disabled={!!busy}
          onClick={() =>
            void run('shed', async () => {
              await api.shedCycles.create({
                status: shedStatus,
                started_at: shedStart,
                completed_at: shedStatus === 'shed' ? shedStart : null,
                quality: shedStatus === 'shed' ? shedQuality : null,
                eyes: shedEyes,
              })
            })
          }
        >
          Log Shed Status
        </Btn>
      </LogForm>

      <LogForm title="Maintenance">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={mDate} onChange={(e) => setMDate(e.target.value)} />
          </Field>
          <Field label="Kind">
            <Select value={mKind} onChange={(e) => setMKind(e.target.value)}>
              <option value="water">Water change</option>
              <option value="substrate">Sub tray</option>
              <option value="deep_clean">Deep clean</option>
            </Select>
          </Field>
          <Field label="Notes">
            <Input value={mNotes} onChange={(e) => setMNotes(e.target.value)} />
          </Field>
        </div>
        <Btn
          disabled={!!busy}
          onClick={() =>
            void run('maint', async () => {
              await api.maintenance.create({ date: mDate, kind: mKind, notes: mNotes })
              setMNotes('')
            })
          }
        >
          Log Maintenance
        </Btn>
      </LogForm>

      <LogForm title="Temp & Humidity">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Hot °F">
            <Input type="number" value={hot} onChange={(e) => setHot(e.target.value)} />
          </Field>
          <Field label="Cool °F">
            <Input type="number" value={cool} onChange={(e) => setCool(e.target.value)} />
          </Field>
          <Field label="Night °F">
            <Input type="number" value={night} onChange={(e) => setNight(e.target.value)} />
          </Field>
          <Field label="Humidity %">
            <Input type="number" value={rh} onChange={(e) => setRh(e.target.value)} />
          </Field>
          <Field label="Notes">
            <Input value={envNotes} onChange={(e) => setEnvNotes(e.target.value)} />
          </Field>
        </div>
        <Btn
          disabled={!!busy || !hot || !cool || !rh}
          onClick={() =>
            void run('env', async () => {
              await api.envReadings.create({
                recorded_at: new Date().toISOString(),
                temp_hot_f: Number(hot),
                temp_cool_f: Number(cool),
                temp_night_f: night ? Number(night) : null,
                humidity_pct: Number(rh),
                notes: envNotes,
              })
              setEnvNotes('')
            })
          }
        >
          Save Reading
        </Btn>
      </LogForm>

      <LogForm title="Photo">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={photoDate} onChange={(e) => setPhotoDate(e.target.value)} />
          </Field>
          <Field label="Kind">
            <Select value={photoKind} onChange={(e) => setPhotoKind(e.target.value)}>
              <option value="growth">Growth</option>
              <option value="shed">Shed</option>
              <option value="body_condition">Body condition</option>
              <option value="other">Other</option>
            </Select>
          </Field>
          <Field label="Caption">
            <Input value={photoCaption} onChange={(e) => setPhotoCaption(e.target.value)} />
          </Field>
          <Field label="File">
            <Input
              type="file"
              accept="image/*"
              onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
            />
          </Field>
        </div>
        <label className="mb-2 flex min-h-11 items-center gap-2 text-[13px] text-bone">
          <input type="checkbox" checked={useAsHero} onChange={(e) => setUseAsHero(e.target.checked)} />
          Use as profile
        </label>
        <Btn
          disabled={!!busy || !photoFile}
          onClick={() =>
            void run('photo', async () => {
              if (!photoFile) return
              const form = new FormData()
              form.append('file', photoFile)
              form.append('taken_at', photoDate)
              form.append('kind', photoKind)
              form.append('caption', photoCaption)
              const photo = await api.photos.upload(form)
              if (useAsHero) await api.setHero(photo.id)
              setPhotoCaption('')
              setPhotoFile(null)
              setUseAsHero(false)
            })
          }
        >
          Upload
        </Btn>
      </LogForm>

      <LogForm title="Log Regurgitation">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={rDate} onChange={(e) => setRDate(e.target.value)} />
          </Field>
          <Field label="Severity">
            <Select value={rSev} onChange={(e) => setRSev(e.target.value)}>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </Select>
          </Field>
          <Field label="Notes">
            <Input
              value={rNotes}
              onChange={(e) => setRNotes(e.target.value)}
              placeholder="Details..."
            />
          </Field>
        </div>
        <Btn
          disabled={!!busy}
          onClick={() =>
            void run('regurg', async () => {
              await api.regurgitations.create({ date: rDate, severity: rSev, notes: rNotes })
              setRNotes('')
            })
          }
        >
          Log Regurg
        </Btn>
      </LogForm>
    </div>
  )
}
