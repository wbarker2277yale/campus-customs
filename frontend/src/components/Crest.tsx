// Heraldic crests for the five agents, drawn in SVG.
// Each obeys the rule of tincture (never metal on metal or colour on colour)
// and is drawn flat, with a heavy outline, in the graphic manner of 1960s
// collegiate shields: Yale's own arms are a blue field with an open book.
import type { Actor } from '../types'

export const T = {
  or: '#C9A43A',      // gold (metal)
  argent: '#F7F3E8',  // silver/white (metal)
  azure: '#1D4E89',   // blue (colour)
  gules: '#9B2A2C',   // red (colour)
  vert: '#2E6A47',    // green (colour)
  sable: '#1C1C1C',   // black (colour)
  outline: '#13284B', // J. Press navy
}

export interface AgentMeta {
  name: string
  role: string
  motto: string
  blazon: string
}

export const AGENTS: Record<Actor, AgentMeta> = {
  boss: {
    name: 'Boss', role: 'Reads each ticket, routes it, makes the final call',
    motto: 'PRIMUS INTER PARES', blazon: 'Azure, a crown Or',
  },
  inventory: {
    name: 'Inventory', role: 'Stock, shortfalls, vendors, purchase orders',
    motto: 'OMNIA NUMERATA', blazon: 'Argent, a chevron Azure between three lozenges Gules',
  },
  accounting: {
    name: 'Accounting', role: 'Cash, invoices, margins, payment requests',
    motto: 'RATIO VINCIT', blazon: 'Vert, three bezants',
  },
  facilities: {
    name: 'Facilities', role: 'The shop space: lease and rent',
    motto: 'DOMUS NOSTRA', blazon: 'Gules, a tower Argent',
  },
  customer_service: {
    name: 'Customer Service', role: 'Drafts to customers, never sent',
    motto: 'VERBA CUM CURA', blazon: 'Or, a quill in bend Sable',
  },
  human: {
    name: 'Will', role: 'The proprietor; approves every payment',
    motto: 'MANU PROPRIA', blazon: 'Azure, an open book Argent (after Yale)',
  },
}

const SHIELD = 'M6 6 H94 V54 C94 88 72 106 50 113 C28 106 6 88 6 54 Z'

function Charge({ agent }: { agent: Actor }) {
  switch (agent) {
    case 'boss':
      return (
        <g fill={T.or} stroke={T.outline} strokeWidth={2.2} strokeLinejoin="round">
          <path d="M26 66 L22 34 L36 48 L50 26 L64 48 L78 34 L74 66 Z" />
          <rect x={24} y={66} width={52} height={10} rx={1.5} />
          <circle cx={50} cy={22} r={4} />
          <circle cx={22} cy={31} r={3.2} />
          <circle cx={78} cy={31} r={3.2} />
        </g>
      )
    case 'inventory':
      return (
        <g stroke={T.outline} strokeWidth={2.2} strokeLinejoin="round">
          <path d="M6 82 L50 44 L94 82 L94 66 L50 28 L6 66 Z" fill={T.azure} />
          {[[24, 22], [76, 22], [50, 92]].map(([x, y]) => (
            <path key={`${x}${y}`} d={`M${x} ${y - 9} L${x + 7} ${y} L${x} ${y + 9} L${x - 7} ${y} Z`} fill={T.gules} />
          ))}
        </g>
      )
    case 'accounting':
      return (
        <g fill={T.or} stroke={T.outline} strokeWidth={2.2}>
          <circle cx={30} cy={34} r={12} />
          <circle cx={70} cy={34} r={12} />
          <circle cx={50} cy={72} r={12} />
        </g>
      )
    case 'facilities':
      return (
        <g fill={T.argent} stroke={T.outline} strokeWidth={2.2} strokeLinejoin="round">
          <path d="M32 92 V42 H28 V26 H36 V32 H44 V26 H56 V32 H64 V26 H72 V42 H68 V92 Z" />
          <path d="M44 92 V74 C44 68 56 68 56 74 V92 Z" fill={T.gules} />
          <rect x={46} y={48} width={8} height={12} rx={4} fill={T.gules} />
        </g>
      )
    case 'customer_service':
      return (
        <g stroke={T.outline} strokeWidth={2.2} strokeLinejoin="round">
          <path d="M24 92 C40 70 58 46 80 20 C84 34 78 52 64 64 C56 72 44 80 30 90 Z" fill={T.sable} />
          <path d="M30 90 L22 100" stroke={T.sable} strokeWidth={3.5} strokeLinecap="round" />
          <path d="M34 82 C48 66 62 48 76 30" stroke={T.or} strokeWidth={1.6} fill="none" />
        </g>
      )
    case 'human':
      return (
        <g stroke={T.outline} strokeWidth={2.2} strokeLinejoin="round">
          <path d="M18 40 C30 34 42 36 50 42 C58 36 70 34 82 40 V78 C70 72 58 72 50 78 C42 72 30 72 18 78 Z" fill={T.argent} />
          <path d="M50 42 V78" />
          <path d="M26 50 H42 M26 58 H42 M58 50 H74 M58 58 H74" strokeWidth={1.4} />
        </g>
      )
  }
}

const FIELD: Record<Actor, string> = {
  boss: T.azure, inventory: T.argent, accounting: T.vert,
  facilities: T.gules, customer_service: T.or, human: T.azure,
}

export function Crest({ agent, size = 72, motto = true, active = false }:
  { agent: Actor; size?: number; motto?: boolean; active?: boolean }) {
  const meta = AGENTS[agent]
  const h = motto ? 136 : 118
  return (
    <svg
      className={`crest${active ? ' crest--active' : ''}`}
      viewBox={`0 0 100 ${h}`} width={size} height={(size * h) / 100}
      role="img" aria-label={`${meta.name}: ${meta.blazon}`}
    >
      <title>{`${meta.name} — ${meta.blazon}`}</title>
      <path d={SHIELD} transform="translate(2.5 3)" fill={T.outline} opacity={0.22} />
      <clipPath id={`clip-${agent}`}><path d={SHIELD} /></clipPath>
      <path d={SHIELD} fill={FIELD[agent]} />
      <g clipPath={`url(#clip-${agent})`}><Charge agent={agent} /></g>
      <path d={SHIELD} fill="none" stroke={T.outline} strokeWidth={4.5} strokeLinejoin="round" />
      <path d={SHIELD} fill="none" stroke={T.or} strokeWidth={1} transform="translate(50 59) scale(0.9) translate(-50 -59)" opacity={0.85} />
      {motto && (
        <g>
          <path d="M4 124 L12 118 H88 L96 124 L88 130 H12 Z" fill={T.argent} stroke={T.outline} strokeWidth={1.8} strokeLinejoin="round" />
          <path d="M4 124 L0 132 L10 130 M96 124 L100 132 L90 130" fill={T.argent} stroke={T.outline} strokeWidth={1.5} strokeLinejoin="round" />
          <text x={50} y={127} textAnchor="middle" fontSize={motto && meta.motto.length > 14 ? 6.4 : 7.4}
                fontFamily="Baskerville, 'Libre Baskerville', Georgia, serif" letterSpacing={0.6} fill={T.outline}>
            {meta.motto}
          </text>
        </g>
      )}
    </svg>
  )
}
