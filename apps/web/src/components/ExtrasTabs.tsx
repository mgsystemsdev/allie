import { useEffect, useState } from 'react'
import { api, getToken, mediaUrl, todayStr, type AppSettings, type Journal, type Photo } from '../api/client'
import { Btn, BtnSm, Empty, Field, Input, LogForm, SectionLabel, Select, TextArea } from './ui'

export function JournalTab() {
  const [rows, setRows] = useState<Journal[]>([])
  const [date, setDate] = useState(todayStr())
  const [body, setBody] = useState('')

  async function load() {
    setRows(await api.journal.list())
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div>
      <SectionLabel>Journal</SectionLabel>
      <LogForm title="New entry">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
        </div>
        <TextArea
          rows={4}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Odd behavior, escape attempts, appetite notes..."
          className="mb-2"
        />
        <Btn
          onClick={async () => {
            if (!body.trim()) return
            await api.journal.create({ date, body })
            setBody('')
            await load()
          }}
        >
          Save Entry
        </Btn>
      </LogForm>
      {rows.length === 0 ? (
        <Empty>No journal entries yet.</Empty>
      ) : (
        <ul className="space-y-3">
          {rows.map((r) => (
            <li key={r.id} className="rounded-[10px] border border-border bg-charcoal p-3.5">
              <div className="mb-1 flex justify-between">
                <span className="font-mono text-[11px] text-sand">{r.date}</span>
                <BtnSm
                  onClick={async () => {
                    await api.journal.remove(r.id)
                    await load()
                  }}
                >
                  ✕
                </BtnSm>
              </div>
              <p className="whitespace-pre-wrap text-[13px] text-bone-dark">{r.body}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function PhotosTab() {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [takenAt, setTakenAt] = useState(todayStr())
  const [kind, setKind] = useState('growth')
  const [caption, setCaption] = useState('')
  const [file, setFile] = useState<File | null>(null)

  async function load() {
    setPhotos(await api.photos.list())
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <div>
      <SectionLabel>Upload photo</SectionLabel>
      <LogForm title="Photo">
        <div className="mb-2 flex flex-wrap gap-2.5">
          <Field label="Date">
            <Input type="date" value={takenAt} onChange={(e) => setTakenAt(e.target.value)} />
          </Field>
          <Field label="Kind">
            <Select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="growth">Growth</option>
              <option value="shed">Shed</option>
              <option value="body_condition">Body condition</option>
              <option value="other">Other</option>
            </Select>
          </Field>
          <Field label="Caption">
            <Input value={caption} onChange={(e) => setCaption(e.target.value)} />
          </Field>
          <Field label="File">
            <Input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </Field>
        </div>
        <Btn
          onClick={async () => {
            if (!file) return
            const form = new FormData()
            form.append('file', file)
            form.append('taken_at', takenAt)
            form.append('kind', kind)
            form.append('caption', caption)
            await api.photos.upload(form)
            setCaption('')
            setFile(null)
            await load()
          }}
        >
          Upload
        </Btn>
      </LogForm>
      {photos.length === 0 ? (
        <Empty>No photos yet.</Empty>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {photos.map((p) => (
            <div key={p.id} className="overflow-hidden rounded-[10px] border border-border-hi bg-bark">
              <img src={mediaUrl(p.url)} alt={p.caption || p.kind} className="aspect-square w-full object-cover" />
              <div className="flex items-start justify-between p-2">
                <div>
                  <div className="font-mono text-[10px] text-sand">
                    {p.taken_at} · {p.kind}
                  </div>
                  <div className="text-[12px] text-bone-dark">{p.caption || '—'}</div>
                </div>
                <BtnSm
                  onClick={async () => {
                    await api.photos.remove(p.id)
                    await load()
                  }}
                >
                  ✕
                </BtnSm>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 border-b border-border py-2 text-[13px] last:border-0">
      <span className="text-bone-dark">{label}</span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  )
}

export function SettingsTab({ onLogout }: { onLogout: () => void }) {
  const [s, setS] = useState<AppSettings | null>(null)
  const [saveMsg, setSaveMsg] = useState('')
  const [testMsg, setTestMsg] = useState('')
  const [pdfMsg, setPdfMsg] = useState('')

  useEffect(() => {
    void api.settings.get().then(setS).catch((e) => setSaveMsg(String(e)))
  }, [])

  function patch<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setS((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  async function downloadPdfToday() {
    setPdfMsg('')
    try {
      const dig = await api.settings.digestToday()
      const title = dig.subject.replace(/</g, '&lt;').replace(/"/g, '&quot;')
      const doc = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>${title}</title>
<style>
  @page { margin: 16mm; }
  body { margin: 0; background: #1a0e08; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style></head><body>
${dig.html}
<script>window.onload=function(){window.print()}</script>
</body></html>`
      const w = window.open('', '_blank')
      if (!w) {
        setPdfMsg('Popup blocked — allow popups, then try again')
        return
      }
      w.document.write(doc)
      w.document.close()
      setPdfMsg(`Opened print dialog for ${dig.date} — choose Save as PDF`)
    } catch (e) {
      setPdfMsg(String(e))
    }
  }

  if (!s) {
    return <div className="text-muted">{saveMsg || 'Loading settings…'}</div>
  }

  return (
    <div>
      <SectionLabel>Today’s digest</SectionLabel>
      <LogForm title="Same content as the care email">
        <p className="mb-2 text-[12px] text-muted">
          Preview and print today’s digest (handle, feed, maintenance, shed, recent activity) — identical to what Resend would send.
        </p>
        <Btn onClick={() => void downloadPdfToday()}>Download PDF today</Btn>
        {pdfMsg && <p className="mt-2 font-mono text-[11px] text-sand">{pdfMsg}</p>}
      </LogForm>

      <SectionLabel>Email delivery</SectionLabel>
      <LogForm title="Resend destination">
        <Toggle label="Enable email notifications" checked={s.email_enabled} onChange={(v) => patch('email_enabled', v)} />
        <div className="mt-2 flex flex-wrap gap-2.5">
          <Field label="Destination email">
            <Input value={s.reminder_email} onChange={(e) => patch('reminder_email', e.target.value)} />
          </Field>
          <Field label="Timezone">
            <Select value={s.timezone} onChange={(e) => patch('timezone', e.target.value)}>
              <option value="America/Chicago">America/Chicago</option>
              <option value="America/New_York">America/New_York</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
              <option value="America/Denver">America/Denver</option>
              <option value="UTC">UTC</option>
            </Select>
          </Field>
        </div>
        <p className="mt-2 text-[11px] text-muted">API key stays in server env (RESEND_API_KEY) — not editable here.</p>
      </LogForm>

      <SectionLabel>Digest schedule</SectionLabel>
      <LogForm title="Twice-daily mini dashboard">
        <Toggle label="Enable digests" checked={s.digest_enabled} onChange={(v) => patch('digest_enabled', v)} />
        <Toggle
          label="Send second digest"
          checked={s.digest_second_enabled}
          onChange={(v) => patch('digest_second_enabled', v)}
        />
        <div className="mt-2 flex flex-wrap gap-2.5">
          <Field label="Digest 1 time">
            <Input type="time" value={s.digest_time_1} onChange={(e) => patch('digest_time_1', e.target.value)} />
          </Field>
          <Field label="Digest 2 time">
            <Input type="time" value={s.digest_time_2} onChange={(e) => patch('digest_time_2', e.target.value)} />
          </Field>
        </div>
        <div className="mt-3 space-y-1">
          <Toggle label="Show clear-to-handle block" checked={s.digest_show_handle} onChange={(v) => patch('digest_show_handle', v)} />
          <Toggle label="Show feed countdown" checked={s.digest_show_feed} onChange={(v) => patch('digest_show_feed', v)} />
          <Toggle label="Show maintenance" checked={s.digest_show_maint} onChange={(v) => patch('digest_show_maint', v)} />
          <Toggle label="Show shed" checked={s.digest_show_shed} onChange={(v) => patch('digest_show_shed', v)} />
          <Toggle label="Show recent activity" checked={s.digest_show_activity} onChange={(v) => patch('digest_show_activity', v)} />
        </div>
      </LogForm>

      <SectionLabel>Care intervals</SectionLabel>
      <LogForm title="KPIs + email countdowns">
        <div className="flex flex-wrap gap-2.5">
          <Field label="Feed prep window (days)">
            <Input
              type="number"
              value={s.feed_ready_days}
              onChange={(e) => patch('feed_ready_days', Number(e.target.value))}
            />
          </Field>
          <Field label="Clear-to-handle hours">
            <Input
              type="number"
              value={s.handle_clear_hours}
              onChange={(e) => patch('handle_clear_hours', Number(e.target.value))}
            />
          </Field>
          <Field label="Max days between handlings">
            <Input
              type="number"
              value={s.handling_max_gap_days}
              onChange={(e) => patch('handling_max_gap_days', Number(e.target.value))}
            />
          </Field>
          <Field label="Water every N days">
            <Input
              type="number"
              value={s.maint_water_days}
              onChange={(e) => patch('maint_water_days', Number(e.target.value))}
            />
          </Field>
          <Field label="Substrate every N days">
            <Input
              type="number"
              value={s.maint_substrate_days}
              onChange={(e) => patch('maint_substrate_days', Number(e.target.value))}
            />
          </Field>
          <Field label="Deep clean every N days">
            <Input
              type="number"
              value={s.maint_deep_clean_days}
              onChange={(e) => patch('maint_deep_clean_days', Number(e.target.value))}
            />
          </Field>
          <Field label="Feed interval mode">
            <Select value={s.feed_interval_mode} onChange={(e) => patch('feed_interval_mode', e.target.value)}>
              <option value="auto">Auto by life stage</option>
              <option value="manual">Manual days</option>
            </Select>
          </Field>
          {s.feed_interval_mode === 'manual' && (
            <Field label="Feed every N days">
              <Input
                type="number"
                value={s.feed_interval_days ?? 8}
                onChange={(e) => patch('feed_interval_days', Number(e.target.value))}
              />
            </Field>
          )}
        </div>
      </LogForm>

      <SectionLabel>Event emails (outside digest)</SectionLabel>
      <LogForm title="One-shot alerts">
        <Toggle
          label="1. Handle cleared (Wait → Clear)"
          checked={s.event_handle_cleared}
          onChange={(v) => patch('event_handle_cleared', v)}
        />
        <Toggle
          label="2. Feed just became overdue"
          checked={s.event_feed_overdue}
          onChange={(v) => patch('event_feed_overdue', v)}
        />
        <Toggle
          label="3. Handling gap exceeded"
          checked={s.event_handling_gap}
          onChange={(v) => patch('event_handling_gap', v)}
        />
        <Toggle
          label="4. Shed entered blue/opaque"
          checked={s.event_shed_status}
          onChange={(v) => patch('event_shed_status', v)}
        />
        <Toggle label="5. Regurgitation logged" checked={s.event_regurg} onChange={(v) => patch('event_regurg', v)} />
      </LogForm>

      <div className="mb-4 flex flex-wrap gap-2">
        <Btn
          onClick={async () => {
            try {
              const saved = await api.settings.update(s)
              setS(saved)
              setSaveMsg('Saved')
            } catch (e) {
              setSaveMsg(String(e))
            }
          }}
        >
          Save settings
        </Btn>
        <Btn
          onClick={async () => {
            try {
              const r = await api.settings.testDigest()
              setTestMsg(JSON.stringify(r))
            } catch (e) {
              setTestMsg(String(e))
            }
          }}
        >
          Send test digest
        </Btn>
      </div>
      {saveMsg && <p className="mb-2 font-mono text-[11px] text-sand">{saveMsg}</p>}
      {testMsg && <p className="mb-4 font-mono text-[11px] text-muted break-all">{testMsg}</p>}

      <SectionLabel>Session</SectionLabel>
      <Btn onClick={onLogout}>Log out</Btn>
    </div>
  )
}

/** Temporary — export / localStorage import. Remove when migration is done. */
export function LocalTab() {
  const [importStatus, setImportStatus] = useState('')
  const [feedsJson, setFeedsJson] = useState('[]')
  const [weightsJson, setWeightsJson] = useState('[]')
  const [shedsJson, setShedsJson] = useState('[]')
  const [vetJson, setVetJson] = useState('[]')

  async function download(url: string, filename: string) {
    const token = getToken()
    const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!res.ok) throw new Error('Export failed')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div>
      <p className="mb-4 rounded-lg border border-border bg-[#2C201A] px-3 py-2 text-[12px] text-sand">
        Temporary local tools — export backups and import old index.html localStorage. Safe to delete this tab later.
      </p>

      <SectionLabel>Export / backup</SectionLabel>
      <div className="mb-4 flex flex-wrap gap-2">
        <Btn onClick={() => void download(api.exportJsonUrl(), 'allie-export.json')}>Download JSON</Btn>
        <Btn onClick={() => void download(api.exportCsvUrl(), 'allie-export.zip')}>Download CSV zip</Btn>
      </div>

      <SectionLabel>Import localStorage (from old index.html)</SectionLabel>
      <p className="mb-2 text-[12px] text-muted">
        Paste JSON arrays from browser localStorage keys: allie_feeds, allie_weights, allie_sheds, allie_vet.
      </p>
      <LogForm title="Import">
        <Field label="allie_feeds JSON">
          <TextArea rows={3} value={feedsJson} onChange={(e) => setFeedsJson(e.target.value)} className="mb-2 font-mono text-[11px]" />
        </Field>
        <Field label="allie_weights JSON">
          <TextArea rows={2} value={weightsJson} onChange={(e) => setWeightsJson(e.target.value)} className="mb-2 font-mono text-[11px]" />
        </Field>
        <Field label="allie_sheds JSON">
          <TextArea rows={2} value={shedsJson} onChange={(e) => setShedsJson(e.target.value)} className="mb-2 font-mono text-[11px]" />
        </Field>
        <Field label="allie_vet JSON">
          <TextArea rows={2} value={vetJson} onChange={(e) => setVetJson(e.target.value)} className="mb-2 font-mono text-[11px]" />
        </Field>
        <Btn
          onClick={async () => {
            try {
              const result = await api.importLocalStorage({
                feeds: JSON.parse(feedsJson),
                weights: JSON.parse(weightsJson),
                sheds: JSON.parse(shedsJson),
                vet: JSON.parse(vetJson),
              })
              setImportStatus(JSON.stringify(result))
            } catch (e) {
              setImportStatus(String(e))
            }
          }}
        >
          Import
        </Btn>
        {importStatus && <p className="mt-2 font-mono text-[11px] text-sand">{importStatus}</p>}
      </LogForm>
    </div>
  )
}
