import type { ReactNode } from 'react'

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="mt-5 mb-2.5 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-muted first:mt-0">
      {children}
      <span className="h-px flex-1 bg-border" />
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-[10px] border border-border-hi bg-bark p-3.5 ${className}`}>{children}</div>
  )
}

export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <div className="mb-1.5 font-mono text-[10px] font-bold uppercase tracking-[0.1em] text-muted">
      {children}
    </div>
  )
}

export function Btn({
  children,
  onClick,
  type = 'button',
  disabled,
}: {
  children: ReactNode
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className="cursor-pointer rounded-[7px] border border-terracotta bg-deep-red px-4 py-2 text-xs font-bold uppercase tracking-[0.06em] text-inverse transition hover:bg-terracotta disabled:opacity-50"
    >
      {children}
    </button>
  )
}

export function BtnSm({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="cursor-pointer rounded-[5px] border border-border-hi bg-bark px-2.5 py-1 font-mono text-[11px] text-muted hover:border-sand hover:text-bone"
    >
      {children}
    </button>
  )
}

export function Field({
  label,
  children,
  className = '',
}: {
  label: string
  children: ReactNode
  className?: string
}) {
  return (
    <label className={`flex min-w-[120px] flex-1 flex-col gap-1 ${className}`}>
      <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted">{label}</span>
      {children}
    </label>
  )
}

const inputCls =
  'w-full rounded-md border border-border-hi bg-bark px-2.5 py-1.5 text-[13px] text-bone outline-none focus:border-sand'

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputCls} ${props.className || ''}`} />
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputCls} ${props.className || ''}`} />
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${inputCls} ${props.className || ''}`} />
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="p-8 text-center text-[13px] text-muted">{children}</div>
}

export function LogForm({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-4 rounded-[10px] border border-border bg-charcoal p-4">
      <div className="mb-3 font-mono text-xs font-bold uppercase tracking-[0.1em] text-sand">{title}</div>
      {children}
    </div>
  )
}
