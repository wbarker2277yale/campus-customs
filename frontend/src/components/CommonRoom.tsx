// The Common Room: the five agents, who is speaking now, and the running
// transcript of their talk and tool use.
import { useEffect, useRef } from 'react'
import type { Line } from '../describe'
import type { Actor, AgentName } from '../types'
import { AGENTS, Crest } from './Crest'

const TEAM: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export function CommonRoom({ lines, speaking, live, status, filter, setFilter }: {
  lines: Line[]
  speaking: Actor | null
  live: boolean
  status: string | null
  filter: number | null
  setFilter: (t: number | null) => void
}) {
  // Scroll only the transcript box (never the page) to the newest line.
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => { if (box.current) box.current.scrollTop = box.current.scrollHeight }, [lines.length])
  const shown = filter == null ? lines : lines.filter(l => l.ticket === filter)
  const tickets = [...new Set(lines.map(l => l.ticket).filter((t): t is number => t != null))].sort()
  return (
    <section className="panel room">
      <header className="panel__head">
        <h2>The Common Room</h2>
        <p>{live ? 'In session — the agents are at work.' : 'Adjourned. The record of past sessions is below.'}</p>
        {status && <div className="heartbeat"><span className="heartbeat__dot" />{status}</div>}
      </header>
      <div className="roster">
        {TEAM.map(a => (
          <figure key={a} className={`member${speaking === a ? ' member--speaking' : ''}`}>
            <Crest agent={a} size={54} active={speaking === a} />
            <figcaption>
              <b>{AGENTS[a].name}</b>
              <span>{AGENTS[a].role}</span>
            </figcaption>
          </figure>
        ))}
      </div>
      <div className="filters">
        <span>Show:</span>
        <button className={filter == null ? 'chip chip--on' : 'chip'} onClick={() => setFilter(null)}>All tickets</button>
        {tickets.map(t => (
          <button key={t} className={filter === t ? 'chip chip--on' : 'chip'} onClick={() => setFilter(t)}>No. {t}</button>
        ))}
      </div>
      <div className="transcript" ref={box}>
        {shown.length === 0 && <p className="transcript__empty">No one has spoken yet. Choose a ticket from the docket to begin.</p>}
        {shown.filter(l => l.agent in AGENTS).map(l => (
          <div key={l.key} className={`line line--${l.tone}`}>
            <Crest agent={l.agent} size={20} motto={false} />
            <div>
              <span className="line__who">{AGENTS[l.agent]?.name ?? l.agent}</span>
              {l.ticket != null && <span className="line__tix">No. {l.ticket}</span>}
              <span className="line__text">{l.text}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
