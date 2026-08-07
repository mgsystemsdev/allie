import { useEffect, useState } from 'react'

/** Live remaining ms until ISO clear_at. Returns 0 when ready/past. */
export function useCountdown(clearAt: string | null | undefined, ready: boolean): {
  msLeft: number
  label: string
  done: boolean
} {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (ready || !clearAt) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [ready, clearAt])

  if (ready || !clearAt) {
    return { msLeft: 0, label: '', done: true }
  }

  const msLeft = Math.max(0, new Date(clearAt).getTime() - now)
  return {
    msLeft,
    label: formatMs(msLeft),
    done: msLeft <= 0,
  }
}

export function formatMs(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const parts: string[] = []
  if (days) parts.push(`${days}d`)
  if (hours || days) parts.push(`${hours}h`)
  parts.push(`${minutes}m`)
  if (!days) parts.push(`${seconds}s`)
  return parts.join(' ')
}
