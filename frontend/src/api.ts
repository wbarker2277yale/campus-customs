// Every call goes to the FastAPI backend on port 8000 (backend/main.py).
import type {
  AuditStep, CashResponse, Health, PaymentsResponse, RunSummary, StartedRun, TicketDetail, TicketsResponse,
} from './types'

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body?.detail ?? `${res.status} ${res.statusText}`)
  return body as T
}

export const api = {
  health: () => call<Health>('/api/health'),
  tickets: () => call<TicketsResponse>('/api/tickets'),
  ticket: (id: number) => call<TicketDetail>(`/api/tickets/${id}`),
  cash: () => call<CashResponse>('/api/cash'),
  payments: () => call<PaymentsResponse>('/api/payments'),
  runs: () => call<{ runs: RunSummary[] }>('/api/runs'),
  activity: (limit = 80) => call<{ run_in_progress: string | null; steps: AuditStep[] }>(`/api/activity?limit=${limit}`),
  runTicket: (id: number) => call<StartedRun>(`/api/tickets/${id}/run`, { method: 'POST' }),
  runAll: (order: number[]) => call<StartedRun>('/api/run-all', { method: 'POST', body: JSON.stringify({ order }) }),
  approve: (requestId: number) => call<Record<string, unknown>>(`/api/payments/${requestId}/approve`, { method: 'POST' }),
  reject: (requestId: number, reason: string) =>
    call<Record<string, unknown>>(`/api/payments/${requestId}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  reset: () => call<{ ok: boolean; note: string }>('/api/reset', { method: 'POST', body: JSON.stringify({ confirm: true }) }),
  stream: (path: string) => new EventSource(`${API_BASE}${path}`),
}

export const money = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
