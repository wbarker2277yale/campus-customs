// Turns audit-trail steps into plain sentences for the Common Room.
import { AGENTS } from './components/Crest'
import type { Actor, AuditStep } from './types'

export interface Line {
  key: string
  agent: Actor
  to?: Actor
  ticket: number | null
  time: string
  tone: 'talk' | 'tool' | 'result' | 'report' | 'done' | 'warn' | 'human'
  text: string
}

const STATUS: Record<string, string> = {
  open: 'Open', in_progress: 'In Progress', awaiting_approval: 'Awaiting Signature', resolved: 'Resolved',
}
const who = (a: string) => AGENTS[a as Actor]?.name ?? a
const clip = (s: string, n = 220) => (s.length > n ? s.slice(0, n - 1) + '…' : s)

function args(a: Record<string, unknown>): string {
  return Object.entries(a)
    .filter(([k]) => !['reason', 'body', 'note', 'task'].includes(k))
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ')
}

export function describe(s: AuditStep): Line[] {
  const base = { agent: s.agent, ticket: s.ticket_id, time: s.time }
  const key = `${s.run_id}-${s.time}-${s.kind}-${s.agent}-${s.step}`
  const d = s.detail
  switch (s.kind) {
    case 'run_start':
      return [{ ...base, key, tone: 'talk', text: s.depth === 0 ? `opens ticket ${s.ticket_id}.` : `takes up: “${clip(d.task)}”` }]
    case 'delegation':
      return [{ ...base, key, to: d.to, tone: 'talk', text: `asks ${who(d.to)}: “${clip(d.task)}”` }]
    case 'model_response': {
      const out: Line[] = []
      ;(d.text ?? []).forEach((t: string, i: number) => out.push({ ...base, key: `${key}-t${i}`, tone: 'talk', text: clip(t) }))
      ;(d.tool_calls ?? []).forEach((c: { tool: string; args?: Record<string, unknown> }, i: number) => {
        if (c.tool === 'delegate') return // shown by the delegation step
        if (c.tool === 'final_result') return
        out.push({ ...base, key: `${key}-c${i}`, tone: 'tool', text: `consults ${c.tool}(${args(c.args ?? {})})` })
      })
      return out
    }
    case 'tool_results':
      return (d.tool_results ?? [])
        .filter((r: { tool: string }) => r.tool !== 'delegate' && r.tool !== 'final_result')
        .map((r: { tool: string; result?: string; retry?: string }, i: number) => ({
          ...base, key: `${key}-r${i}`, tone: r.retry ? 'warn' : 'result',
          text: `${r.tool} → ${clip(r.result ?? r.retry ?? '', 180)}`,
        }))
    case 'run_end':
      return [{ ...base, key, tone: 'report', text: `reports: ${clip(d.report?.summary ?? '', 320)}` }]
    case 'ticket_done':
      return [{ ...base, key, tone: d.stopped === 'completed' ? 'done' : 'warn',
        text: d.stopped === 'completed'
          ? `run finished. Ticket ${s.ticket_id} is now ${STATUS[d.final_status] ?? 'unchanged'}.`
          : `run stopped early (${clip(String(d.stopped), 160)}). Ticket ${s.ticket_id} stays ${STATUS[d.final_status] ?? 'as it was'}.` }]
    case 'limit_stop':
    case 'error':
      return [{ ...base, key, tone: 'warn', text: `stopped: ${clip(d.reason ?? '', 240)}` }]
    case 'human_action': {
      const a = d.action as string
      const text = a === 'approve_payment' ? `approves payment request ${d.request_id}.`
        : a === 'reject_payment' ? `declines payment request ${d.request_id}: “${String(d.reason).replace(/[.!?]+$/, '')}.”`
        : a === 'reset_database' ? 'restores the shop to opening day.' : a
      return [{ ...base, key, tone: 'human', text }]
    }
    default:
      return []
  }
}
