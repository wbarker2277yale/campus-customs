// Shapes returned by backend/main.py (Problem 7 routes).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'
export type Actor = AgentName | 'human'
export type TicketStatus = 'open' | 'in_progress' | 'awaiting_approval' | 'resolved'

export interface TicketRow {
  id: number
  subject: string
  requester: string
  type: string
  status: TicketStatus
}

export interface TicketsResponse {
  date_today: string
  count: number
  tickets: TicketRow[]
}

export interface TicketDetail {
  date_today: string
  ticket: TicketRow & { notes: string | null; sku: string | null; size: string | null; qty: number | null }
  shortfall?: number
}

export interface AuditStep {
  time: string
  run_id: string
  ticket_id: number | null
  agent: Actor
  chain: string[]
  depth: number
  step: number
  kind:
    | 'run_start' | 'model_request' | 'model_response' | 'tool_results' | 'delegation'
    | 'run_end' | 'limit_stop' | 'error' | 'ticket_done' | 'human_action'
  model: string
  detail: Record<string, any>
  usage: Record<string, number>
}

export interface RunSummary {
  run_id: string
  ticket_id: number | null
  started: string
  finished: string | null
  outcome: string
  final_status: TicketStatus | null
  summary: string | null
  agents: Actor[]
  delegations: number
  total_tokens: number
  steps: number
}

export interface PaymentRequest {
  id: number
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number
  ticket_id: number | null
  amount: number
  requested_by: string
  reason: string | null
  status: 'pending_approval' | 'rejected' | 'paid'
  requested_at: string
  decided_by: string | null
}

export interface Payment {
  id: number
  kind: string
  ref_id: number
  amount: number
  paid_at: string
  approved_by: string
}

export interface PaymentsResponse {
  cash_on_hand: number
  payments: Payment[]
  payment_requests: PaymentRequest[]
  pending_total: number
}

export interface CashResponse {
  date_today: string
  checking_balance: number
  as_of: string
  pending_requests_total: number
  balance_after_pending: number
  cash_floor: number
}

export interface StartedRun {
  run_id: string
  ticket_ids: number[]
  run_ids: string[]
  stream: string
}

export interface Health {
  ok: boolean
  model: string
  portkey_key_set: boolean
  approver_name: string | null
  run_in_progress: string | null
}
