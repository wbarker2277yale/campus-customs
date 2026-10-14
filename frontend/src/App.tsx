// Campus Customs — the agents' board. Calls the Problem 7 routes in backend/main.py.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import { Approvals } from './components/Approvals'
import { CashTracker } from './components/CashTracker'
import { CommonRoom } from './components/CommonRoom'
import { AGENTS, Crest } from './components/Crest'
import { Docket } from './components/Docket'
import { describe, type Line } from './describe'
import type { Actor, AuditStep, CashResponse, Health, PaymentsResponse, RunSummary, TicketRow } from './types'

const POLL_MS = 4000

function longDate(iso?: string) {
  if (!iso) return ''
  return new Date(`${iso}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [tickets, setTickets] = useState<TicketRow[]>([])
  const [today, setToday] = useState<string>()
  const [order, setOrder] = useState<number[]>([])
  const [cash, setCash] = useState<CashResponse | null>(null)
  const [cashHistory, setCashHistory] = useState<number[]>([])
  const [pay, setPay] = useState<PaymentsResponse | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [steps, setSteps] = useState<AuditStep[]>([])
  const [liveRun, setLiveRun] = useState<string | null>(null)
  // ?ticket=101 opens the board filtered to one ticket (used for the resolved-board screenshots).
  const [filter, setFilter] = useState<number | null>(() => Number(new URLSearchParams(location.search).get('ticket')) || null)
  const [error, setError] = useState<string | null>(null)
  const source = useRef<EventSource | null>(null)
  const wasRunning = useRef(false)
  const [now, setNow] = useState(() => Date.now())

  // Light poll (health, tickets, cash, payments) every few seconds; the heavier
  // audit-trail reads (runs, activity) only on load, after a run, and after an action.
  const loadRecord = useCallback(async () => {
    const [r, a] = await Promise.all([api.runs(), api.activity(200)])
    setRuns(r.runs)
    if (!source.current) setSteps(a.steps)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [h, t, c, p] = await Promise.all([api.health(), api.tickets(), api.cash(), api.payments()])
      setHealth(h); setTickets(t.tickets); setToday(t.date_today); setCash(c); setPay(p)
      setCashHistory(hist => (hist[hist.length - 1] === c.checking_balance ? hist : [...hist, c.checking_balance].slice(-40)))
      setOrder(o => {
        const ids = t.tickets.map(x => x.id)
        const kept = o.filter(id => ids.includes(id))
        return [...kept, ...ids.filter(id => !kept.includes(id))]
      })
      if (h.run_in_progress) {
        wasRunning.current = true
        // No live stream (page opened mid-run, or the stream dropped): follow the record instead.
        if (!source.current) loadRecord()
      } else if (wasRunning.current) {
        // A run just ended: close any stream and reload the record once.
        wasRunning.current = false
        source.current?.close(); source.current = null; setLiveRun(null)
        loadRecord()
      }
      setError(null)
    } catch (e) {
      setError(`The backend on port 8000 is not answering (${(e as Error).message}).`)
    }
  }, [loadRecord])

  useEffect(() => {
    refresh(); loadRecord()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh, loadRecord])

  // A one-second clock for the "working… N s" heartbeat during a run.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const watch = useCallback((runId: string, stream: string) => {
    source.current?.close()
    setLiveRun(runId)
    wasRunning.current = true
    const es = api.stream(stream)
    source.current = es
    es.addEventListener('step', ev => {
      const row = JSON.parse((ev as MessageEvent).data) as AuditStep
      setSteps(s => [...s, row])
    })
    es.addEventListener('done', () => { es.close(); source.current = null; setLiveRun(null); refresh(); loadRecord() })
    // If the stream drops mid-run, the 4-second poll takes over (see refresh).
    es.onerror = () => { es.close(); source.current = null; refresh() }
  }, [refresh, loadRecord])

  const act = async (fn: () => Promise<unknown>) => {
    try { await fn(); setError(null) } catch (e) { setError((e as Error).message) }
    refresh(); loadRecord()
  }

  const lines: Line[] = useMemo(() => steps.flatMap(describe), [steps])
  const speaking: Actor | null = liveRun ? (steps[steps.length - 1]?.agent ?? null) : null
  const lastRun = useMemo(() => {
    // All runs on a ticket since the last reset, combined: every agent that took
    // part, total delegations and tokens, and the latest Boss summary and outcome.
    const resetAt = steps.filter(s => s.kind === 'human_action' && s.detail.action === 'reset_database').at(-1)?.time ?? ''
    const out: Record<number, RunSummary | undefined> = {}
    for (const r of runs) { // newest first
      if (r.ticket_id == null || r.started < resetAt) continue
      const prev = out[r.ticket_id]
      out[r.ticket_id] = prev
        ? { ...prev, agents: [...new Set([...prev.agents, ...r.agents])], delegations: prev.delegations + r.delegations,
            total_tokens: prev.total_tokens + r.total_tokens }
        : { ...r }
    }
    return out
  }, [runs, steps])
  const busy = Boolean(liveRun || health?.run_in_progress)
  const last = steps[steps.length - 1]
  const quiet = last ? Math.max(0, Math.round((now - Date.parse(last.time)) / 1000)) : 0
  const status = !busy ? null
    : last && last.kind !== 'ticket_done' && last.kind !== 'human_action'
      ? `${AGENTS[last.agent]?.name ?? last.agent} is working on ticket ${last.ticket_id ?? '—'} · ${quiet} s since the last step`
      : 'Starting the next ticket…'

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead__crest"><Crest agent="human" size={64} motto={false} /></div>
        <div className="masthead__title">
          <div className="masthead__eyebrow">Clothiers to the University · New Haven</div>
          <h1>Campus Customs</h1>
          <div className="masthead__sub">The Agents’ Board · {longDate(today)}</div>
        </div>
        <CashTracker cash={cash} history={cashHistory} />
      </header>
      <div className="tartan" aria-hidden />

      {error && <div className="notice">{error}</div>}

      <main className="grid">
        <Docket
          tickets={tickets} order={order} setOrder={setOrder} lastRun={lastRun} busy={busy} focus={filter}
          pendingFor={(pay?.payment_requests ?? []).filter(r => r.status === 'pending_approval' && r.ticket_id != null).map(r => r.ticket_id as number)}
          onRun={id => act(async () => { const r = await api.runTicket(id); watch(r.run_id, r.stream) })}
          onRunAll={() => act(async () => {
            const r = await api.runAll(order.filter(id => tickets.find(t => t.id === id)?.status !== 'resolved'))
            watch(r.run_id, r.stream)
          })}
        />
        <CommonRoom lines={lines} speaking={speaking} live={busy} status={status} filter={filter} setFilter={setFilter} />
        <Approvals
          requests={pay?.payment_requests ?? []} payments={pay?.payments ?? []} cash={cash}
          approver={health?.approver_name ?? null}
          onApprove={id => act(() => api.approve(id))}
          onReject={(id, reason) => act(() => api.reject(id, reason))}
        />
      </main>

      <footer className="colophon">
        <span>Every agent runs on {health?.model ?? 'gpt-6-luna'} through Portkey · every step is kept in output/audit_trail.json</span>
        <button className="btn btn--ghost" disabled={busy} onClick={() => {
          if (window.confirm('Restore the shop to opening day? Tickets, cash, and stock return to their original values. The audit trail is kept.')) {
            act(() => api.reset())
          }
        }}>Restore opening day</button>
      </footer>
    </div>
  )
}
