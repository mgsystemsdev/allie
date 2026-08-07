const TOKEN_KEY = 'allie_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    clearToken()
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  if (res.status === 204) return undefined as T
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res as unknown as T
}

export const api = {
  login: (password: string) =>
    request<{ token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),
  animal: () => request<AnimalOverview>('/api/animal'),
  feeding: {
    config: () => request<FeedingConfig>('/api/feeding/config'),
    recommend: (prey?: string | null) => {
      const q = prey != null && prey !== '' ? `?prey=${encodeURIComponent(prey)}` : ''
      return request<FeedingRecommendation>(`/api/feeding/recommend${q}`)
    },
  },
  feeds: {
    list: () => request<Feed[]>('/api/feeds'),
    create: (body: FeedCreate) =>
      request<Feed>('/api/feeds', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/feeds/${id}`, { method: 'DELETE' }),
  },
  weights: {
    list: () => request<Weight[]>('/api/weights'),
    create: (body: { date: string; weight_g: number }) =>
      request<Weight>('/api/weights', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/weights/${id}`, { method: 'DELETE' }),
  },
  handlings: {
    list: () => request<Handling[]>('/api/handlings'),
    create: (body: HandlingCreate) =>
      request<Handling>('/api/handlings', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/handlings/${id}`, { method: 'DELETE' }),
  },
  regurgitations: {
    list: () => request<Regurg[]>('/api/regurgitations'),
    create: (body: RegurgCreate) =>
      request<Regurg>('/api/regurgitations', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/regurgitations/${id}`, { method: 'DELETE' }),
  },
  shedCycles: {
    list: () => request<ShedCycle[]>('/api/shed-cycles'),
    create: (body: ShedCreate) =>
      request<ShedCycle>('/api/shed-cycles', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: number, body: Partial<ShedCreate>) =>
      request<ShedCycle>(`/api/shed-cycles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/shed-cycles/${id}`, { method: 'DELETE' }),
  },
  envReadings: {
    list: () => request<EnvReading[]>('/api/env-readings'),
    create: (body: EnvCreate) =>
      request<EnvReading>('/api/env-readings', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/env-readings/${id}`, { method: 'DELETE' }),
  },
  eliminations: {
    list: () => request<Elimination[]>('/api/eliminations'),
    create: (body: EliminationCreate) =>
      request<Elimination>('/api/eliminations', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/eliminations/${id}`, { method: 'DELETE' }),
  },
  vetVisits: {
    list: () => request<VetVisit[]>('/api/vet-visits'),
    create: (body: VetCreate) =>
      request<VetVisit>('/api/vet-visits', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/vet-visits/${id}`, { method: 'DELETE' }),
  },
  maintenance: {
    list: () => request<Maint[]>('/api/maintenance'),
    create: (body: MaintCreate) =>
      request<Maint>('/api/maintenance', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/maintenance/${id}`, { method: 'DELETE' }),
  },
  treatments: {
    list: () => request<Treatment[]>('/api/treatments'),
    create: (body: TreatmentCreate) =>
      request<Treatment>('/api/treatments', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/treatments/${id}`, { method: 'DELETE' }),
  },
  contacts: {
    list: () => request<Contact[]>('/api/contacts'),
    create: (body: ContactCreate) =>
      request<Contact>('/api/contacts', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/contacts/${id}`, { method: 'DELETE' }),
  },
  journal: {
    list: () => request<Journal[]>('/api/journal'),
    create: (body: { date: string; body: string }) =>
      request<Journal>('/api/journal', { method: 'POST', body: JSON.stringify(body) }),
    remove: (id: number) => request(`/api/journal/${id}`, { method: 'DELETE' }),
  },
  photos: {
    list: () => request<Photo[]>('/api/photos'),
    upload: async (form: FormData) => {
      const token = getToken()
      const res = await fetch(`${API_BASE}/api/photos`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      return res.json() as Promise<Photo>
    },
    remove: (id: number) => request(`/api/photos/${id}`, { method: 'DELETE' }),
  },
  exportJsonUrl: () => `${API_BASE}/api/export.json`,
  exportCsvUrl: () => `${API_BASE}/api/export.csv`,
  importLocalStorage: (body: {
    feeds: unknown[]
    weights: unknown[]
    sheds: unknown[]
    vet: unknown[]
  }) =>
    request('/api/import/localstorage', { method: 'POST', body: JSON.stringify(body) }),
  settings: {
    get: () => request<AppSettings>('/api/settings'),
    update: (body: Partial<AppSettings>) =>
      request<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
    testDigest: () => request<Record<string, unknown>>('/api/settings/test-digest', { method: 'POST' }),
    digestToday: () =>
      request<{
        ok: boolean
        date: string
        subject: string
        html: string
        text: string
        to: string
      }>('/api/settings/digest-today'),
  },
}

export function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export function mediaUrl(path: string) {
  if (path.startsWith('http')) return path
  return `${API_BASE}${path}`
}

export type Reminder = { kind: string; message: string; severity: string }

export type PreyStatus =
  | 'recommended'
  | 'acceptable'
  | 'too_small'
  | 'too_large'
  | 'alternative'
  | 'unknown'

export type FeedingInterval = {
  min_days: number
  max_days: number
  recommended_days: number
}

export type FeedingStageRules = {
  desc: string
  recommended: string[]
  acceptable: string[]
  alternative: string[]
  feeding_interval: FeedingInterval
}

export type FeedingRecommendation = {
  stage: string
  selected_prey: string | null
  prey_status: PreyStatus | null
  recommended_prey: string[]
  acceptable_prey: string[]
  alternative_prey: string[]
  feeding_interval: FeedingInterval
  prey_status_by_category: Record<string, PreyStatus>
}

export type FeedingConfig = {
  prey_categories: string[]
  stages: Record<string, FeedingStageRules>
}

export type AnimalOverview = {
  id: number
  name: string
  species: string
  common_name: string
  dob: string
  sex: string
  owner: string
  status: string
  age: { months: number; days: number; total: number }
  stage: { label: string; desc: string; feed_interval_days: number }
  prey_categories: string[]
  feeding_stages: Record<string, FeedingStageRules>
  feeding_recommendation: FeedingRecommendation
  total_feeds: number
  last_feed: { id: number; date: string; prey_type: string; accepted: boolean } | null
  next_feed: {
    due_date: string
    days_until: number
    last_feed_date: string
    interval_days: number
  } | null
  next_maintenance: {
    kind: string
    label: string
    due_date: string
    days_until: number
    last_date: string | null
    interval_days: number
  } | null
  handling_gap: {
    last_date: string | null
    days_since: number | null
    max_gap_days: number
    overdue: boolean
    countdown: string
  }
  current_weight_g: number | null
  current_weight_date: string | null
  last_shed: { id: number; date: string; quality: string | null } | null
  clear_to_handle: {
    ready: boolean
    hours_since_feed: number | null
    clear_after_hours: number
    hours_left?: number
    seconds_left?: number
    clear_at?: string | null
    timer_started_at?: string | null
    countdown?: string | null
    message: string
  }
  shed_mode: {
    active: boolean
    status: string
    humidity_target: string
    dont_feed: boolean
    started_at: string | null
  }
  reminders: Reminder[]
}

export type Feed = {
  id: number
  date: string
  prey_type: string
  prey_weight_g: number | null
  accepted: boolean
  snake_weight_g: number | null
  notes: string
}
export type FeedCreate = {
  date: string
  prey_type: string
  prey_weight_g?: number | null
  accepted: boolean
  snake_weight_g?: number | null
  notes?: string
}
export type Weight = { id: number; date: string; weight_g: number }
export type Handling = {
  id: number
  date: string
  duration_min: number
  temperament: string
  notes: string
}
export type HandlingCreate = {
  date: string
  duration_min: number
  temperament: string
  notes?: string
}
export type Regurg = {
  id: number
  date: string
  related_feed_id: number | null
  notes: string
  severity: string
}
export type RegurgCreate = {
  date: string
  related_feed_id?: number | null
  notes?: string
  severity?: string
}
export type ShedCycle = {
  id: number
  status: string
  started_at: string
  completed_at: string | null
  quality: string | null
  eyes: string | null
  notes: string
}
export type ShedCreate = {
  status: string
  started_at: string
  completed_at?: string | null
  quality?: string | null
  eyes?: string | null
  notes?: string
}
export type EnvReading = {
  id: number
  recorded_at: string
  temp_hot_f: number
  temp_cool_f: number
  temp_night_f: number | null
  humidity_pct: number
  notes: string
}
export type EnvCreate = {
  recorded_at: string
  temp_hot_f: number
  temp_cool_f: number
  temp_night_f?: number | null
  humidity_pct: number
  notes?: string
}
export type Elimination = {
  id: number
  date: string
  kind: string
  related_feed_id: number | null
  notes: string
}
export type EliminationCreate = {
  date: string
  kind: string
  related_feed_id?: number | null
  notes?: string
}
export type VetVisit = { id: number; date: string; reason: string; notes: string }
export type VetCreate = { date: string; reason: string; notes?: string }
export type Maint = { id: number; date: string; kind: string; notes: string }
export type MaintCreate = { date: string; kind: string; notes?: string }
export type Treatment = {
  id: number
  started_at: string
  ended_at: string | null
  name: string
  reason: string
  notes: string
}
export type TreatmentCreate = {
  started_at: string
  ended_at?: string | null
  name: string
  reason?: string
  notes?: string
}
export type Contact = {
  id: number
  label: string
  phone: string
  clinic: string
  is_emergency: boolean
}
export type ContactCreate = {
  label: string
  phone?: string
  clinic?: string
  is_emergency?: boolean
}
export type Journal = { id: number; date: string; body: string }
export type Photo = {
  id: number
  taken_at: string
  kind: string
  file_path: string
  caption: string
  url: string
}

export type AppSettings = {
  email_enabled: boolean
  reminder_email: string
  timezone: string
  digest_enabled: boolean
  digest_time_1: string
  digest_time_2: string
  digest_second_enabled: boolean
  feed_ready_days: number
  handle_clear_hours: number
  handling_max_gap_days: number
  maint_water_days: number
  maint_substrate_days: number
  maint_deep_clean_days: number
  feed_interval_mode: string
  feed_interval_days: number | null
  event_handle_cleared: boolean
  event_feed_overdue: boolean
  event_handling_gap: boolean
  event_shed_status: boolean
  event_regurg: boolean
  digest_show_feed: boolean
  digest_show_maint: boolean
  digest_show_shed: boolean
  digest_show_handle: boolean
  digest_show_activity: boolean
}
