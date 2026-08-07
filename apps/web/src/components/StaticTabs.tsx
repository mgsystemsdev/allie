import { Card, SectionLabel } from './ui'
import type { AnimalOverview } from '../api/client'

const STAGE_ORDER = ['Hatchling', 'Juvenile', 'Sub-adult', 'Adult'] as const

export function PreyTab({ animal }: { animal: AnimalOverview }) {
  const current = animal.stage.label
  const alt = animal.feeding_recommendation.alternative_prey

  return (
    <div>
      <p className="mb-3.5 text-[13px] text-muted">
        Allie is a <strong className="text-sand">{current.toLowerCase()}</strong> (
        {animal.age.months} mo). Recommended prey highlighted from age-based rules. All prey
        frozen/thawed.
      </p>
      <SectionLabel>Bird / other prey</SectionLabel>
      <Card className="mb-3.5 text-[13px] text-bone-dark leading-relaxed">
        For {current}:{' '}
        {alt.length > 0 ? (
          <>
            <strong className="text-sand">{alt.join(', ')}</strong> as occasional alternative only.
          </>
        ) : (
          <>no bird/other alternatives listed for this stage.</>
        )}{' '}
        Use sparingly.
      </Card>
      <SectionLabel>Prey by life stage</SectionLabel>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border bg-charcoal text-left font-mono text-[10px] uppercase tracking-[0.1em] text-muted">
            <th className="px-2.5 py-1.5">Life Stage</th>
            <th className="px-2.5 py-1.5">Age</th>
            <th className="px-2.5 py-1.5">Recommended</th>
            <th className="px-2.5 py-1.5">Acceptable</th>
            <th className="px-2.5 py-1.5">Frequency</th>
          </tr>
        </thead>
        <tbody className="text-[12px] text-bone-dark">
          {STAGE_ORDER.map((label) => {
            const rules = animal.feeding_stages[label]
            if (!rules) return null
            const cur = label === current
            const iv = rules.feeding_interval
            return (
              <tr
                key={label}
                className={`border-b border-[#3a2415] ${cur ? 'border-l-[3px] border-l-sand bg-[#4a2c14] text-bone' : ''}`}
              >
                <td className="px-2.5 py-2">{cur ? `★ ${label}` : label}</td>
                <td className="px-2.5 py-2">{rules.desc}</td>
                <td className="px-2.5 py-2">{rules.recommended.join(', ')}</td>
                <td className="px-2.5 py-2">{rules.acceptable.join(', ')}</td>
                <td className="px-2.5 py-2">
                  Every {iv.min_days}–{iv.max_days} days
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <SectionLabel>Category rule</SectionLabel>
      <Card className="text-[13px] leading-relaxed text-bone-dark">
        Pick a prey category from the list. Age sets the stage; stage sets recommended vs acceptable
        vs too small / too large. Grams are optional logging only — not used for recommendations.
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
