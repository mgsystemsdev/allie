import { Card, SectionLabel } from './ui'

export function PreyTab() {
  return (
    <div>
      <p className="mb-3.5 text-[13px] text-muted">
        Allie is a <strong className="text-sand">juvenile</strong>. Recommended prey row is highlighted. All
        prey frozen/thawed.
      </p>
      <SectionLabel>Bird prey</SectionLabel>
      <Card className="mb-3.5 text-[13px] text-bone-dark leading-relaxed">
        At juvenile stage, <strong className="text-sand">day-old chicks</strong> are occasional variety only.
        Quail for sub-adult (~1.5 kg+). Birds are high fat — use sparingly.
      </Card>
      <SectionLabel>Prey size guide</SectionLabel>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border bg-charcoal text-left font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
            <th className="px-2.5 py-1.5">Life Stage</th>
            <th className="px-2.5 py-1.5">Age / Size</th>
            <th className="px-2.5 py-1.5">Prey Item</th>
            <th className="px-2.5 py-1.5">Prey Weight</th>
            <th className="px-2.5 py-1.5">Frequency</th>
          </tr>
        </thead>
        <tbody className="text-[12px] text-bone-dark">
          {[
            ['Hatchling', '0–3 mo / <50g', 'Pinky → Fuzzy mouse', '3–8g', 'Every 5–7 days'],
            ['Young juvenile', '3–6 mo / 50–150g', 'Small mouse', '10–18g', 'Every 7 days'],
            ['Juvenile ★ Allie', '6–12 mo / 150–400g', 'Adult mouse / small rat', '20–50g', 'Every 7–10 days', true],
            ['Sub-adult', '1–2 yr / 400g–1kg', 'Small–medium rat', '60–150g', 'Every 10–14 days'],
            ['Adult', '2–3+ yr / 1–2.5kg', 'Med–large rat / quail', '180–350g', 'Every 14–21 days'],
            ['Large adult', '3+ yr / 2+ kg', 'Large rat / rabbit / pigeon', '300–500g', 'Every 21 days'],
          ].map((row) => (
            <tr
              key={String(row[0])}
              className={`border-b border-[#3a2415] ${row[5] ? 'border-l-[3px] border-l-sand bg-[#4a2c14] text-bone' : ''}`}
            >
              {row.slice(0, 5).map((c, i) => (
                <td key={i} className="px-2.5 py-2">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <SectionLabel>Sizing rule</SectionLabel>
      <Card className="text-[13px] leading-relaxed text-bone-dark">
        Prey should be no wider than <span className="font-bold text-sand">1.0–1.5×</span> the widest point of
        Allie&apos;s body. A slight visible lump after feeding is perfect.
      </Card>
    </div>
  )
}

export function SpeciesTab() {
  const facts: [string, string][] = [
    ['Origin', 'Central Australia — Alice Springs region'],
    ['Habitat', 'Arid rocky gorges, mulga scrub'],
    ['Adult length', '1.8–2.5 m (6–8 ft)'],
    ['Adult weight', '1.5–3 kg (3–7 lb)'],
    ['Lifespan (captive)', '20–30 years'],
    ['Sexual maturity', '3–4 years'],
    ['Activity pattern', 'Primarily nocturnal / crepuscular'],
    ['Temperament', 'Bold, curious — nippy as hatchling, settles with handling'],
    ['Feeding method', 'Constriction'],
    ['Conservation status', 'Least Concern (IUCN)'],
  ]
  return (
    <div>
      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card>
          <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">Scientific name</div>
          <div className="mt-1 font-mono text-sm italic text-bone">Morelia bredli</div>
        </Card>
        <Card>
          <div className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted">Common names</div>
          <div className="mt-1 text-[13px] text-bone-dark">Centralian carpet python, Bredl&apos;s python</div>
        </Card>
      </div>
      <SectionLabel>Key facts</SectionLabel>
      <Card>
        {facts.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between border-b border-border py-2 text-[13px] last:border-0">
            <span className="text-muted">{k}</span>
            <span className="text-right text-bone">{v}</span>
          </div>
        ))}
      </Card>
      <SectionLabel>Handling tips</SectionLabel>
      <Card>
        {[
          ['After feeding', '48–72 hrs minimum — no exceptions'],
          ['Session length', '15–30 min max for juveniles'],
          ['Approach', 'From the side, not above'],
          ['Frequency', '2–3× per week once settled'],
        ].map(([k, v]) => (
          <div key={k} className="flex items-center justify-between border-b border-border py-2 text-[13px] last:border-0">
            <span className="text-muted">{k}</span>
            <span className="text-right text-bone">{v}</span>
          </div>
        ))}
      </Card>
    </div>
  )
}
