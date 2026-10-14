// The docket: the three tickets, Will's chosen order, status stamps, and a
// summary of the agents' last run on each ticket.
import { useEffect, useRef } from 'react'
import type { AgentName, RunSummary, TicketRow } from '../types'
import { AGENTS, Crest } from './Crest'

const STAMP: Record<string, string> = {
  open: 'Open', in_progress: 'In Progress', awaiting_approval: 'Awaiting Signature', resolved: 'Resolved',
}

export function Docket({ tickets, order, setOrder, lastRun, busy, onRun, onRunAll, focus = null }: {
  tickets: TicketRow[]
  order: number[]
  setOrder: (o: number[]) => void
  lastRun: Record<number, RunSummary | undefined>
  busy: boolean
  onRun: (id: number) => void
  onRunAll: () => void
  focus?: number | null
}) {
  // Scroll only this panel (never the page) to the focused ticket's card.
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    const card = panel.current?.querySelector<HTMLElement>(`[data-ticket="${focus}"]`)
    if (panel.current && card) panel.current.scrollTop = card.offsetTop - panel.current.offsetTop - 8
  }, [focus, tickets.length])
  const byId = Object.fromEntries(tickets.map(t => [t.id, t]))
  const ordered = order.map(id => byId[id]).filter(Boolean)
  const move = (i: number, d: -1 | 1) => {
    const o = [...order]; const j = i + d
    if (j < 0 || j >= o.length) return
    ;[o[i], o[j]] = [o[j], o[i]]; setOrder(o)
  }
  const workable = ordered.filter(t => t.status !== 'resolved')
  const team = (agents: string[]) => agents.filter((a): a is AgentName => a in AGENTS && a !== 'human')
  return (
    <section className="panel docket" ref={panel}>
      <header className="panel__head">
        <h2>The Docket</h2>
        <p>Set the order of work, then begin with the first, or work them all in turn.</p>
      </header>
      {ordered.map((t, i) => {
        const run = lastRun[t.id]
        return (
          <article key={t.id} data-ticket={t.id} className={`ticket ticket--${t.status}${focus === t.id ? ' ticket--focus' : ''}`}>
            <div className="ticket__order">
              <span className="ticket__rank">{['First', 'Second', 'Third', 'Fourth', 'Fifth'][i] ?? `${i + 1}th`}</span>
              <button className="arrow" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}>▲</button>
              <button className="arrow" aria-label="Move down" disabled={i === ordered.length - 1} onClick={() => move(i, 1)}>▼</button>
            </div>
            <div className="ticket__body">
              <div className="ticket__no">No. {t.id} · {t.type.replace('_', ' ')}</div>
              <h3>{t.subject}</h3>
              <div className="ticket__from">from {t.requester}</div>
              <div className={`stamp stamp--${t.status}`}>{STAMP[t.status] ?? t.status}</div>
              {run ? (
                <div className="ticket__summary">
                  <div className="ticket__crests">
                    {team(run.agents).map(a => <Crest key={a} agent={a} size={22} motto={false} />)}
                    <span>{team(run.agents).map(a => AGENTS[a].name).join(' · ')}</span>
                  </div>
                  {run.summary && <p>“{run.summary}”</p>}
                  <div className="ticket__meta">
                    {run.delegations} delegation{run.delegations === 1 ? '' : 's'} · {run.total_tokens.toLocaleString()} tokens since reset ·{' '}
                    last run {run.outcome === 'completed' ? 'finished' : 'stopped early'}
                  </div>
                </div>
              ) : (
                <div className="ticket__summary ticket__summary--none">No agent has worked this ticket yet.</div>
              )}
              <button className="btn" disabled={busy || t.status === 'resolved'} onClick={() => onRun(t.id)}>
                Work this ticket
              </button>
            </div>
          </article>
        )
      })}
      <button className="btn btn--primary btn--wide" disabled={busy || workable.length === 0} onClick={onRunAll}>
        Work all, in this order
      </button>
      <p className="fine">Each ticket is capped at 150,000 tokens, and only one run happens at a time.</p>
    </section>
  )
}
