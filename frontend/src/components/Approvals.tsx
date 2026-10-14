// Human approval: every pending payment request waits here for Will's signature.
import { useState } from 'react'
import { money } from '../api'
import type { CashResponse, Payment, PaymentRequest } from '../types'

const KIND: Record<string, string> = { invoice: 'Vendor invoice', rent: 'Rent', purchase_order: 'Purchase order' }

export function Approvals({ requests, payments, cash, approver, onApprove, onReject }: {
  requests: PaymentRequest[]
  payments: Payment[]
  cash: CashResponse | null
  approver: string | null
  onApprove: (id: number) => Promise<void>
  onReject: (id: number, reason: string) => Promise<void>
}) {
  const [declining, setDeclining] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  // Oldest first: the order Accounting filed them, which is Will's payment order.
  const pending = requests.filter(r => r.status === 'pending_approval').sort((a, b) => a.id - b.id)
  let running = cash?.checking_balance ?? 0
  return (
    <section className="panel approvals">
      <header className="panel__head">
        <h2>Awaiting Your Signature</h2>
        <p>Nothing is paid until you sign. Signed as {approver ?? '—'}.</p>
      </header>
      {pending.length === 0 && <p className="quiet">No requests are waiting.</p>}
      {pending.map(r => {
        running -= r.amount
        const below = cash != null && running < cash.cash_floor
        return (
          <div key={r.id} className={`request${below ? ' request--below' : ''}`}>
            <div className="request__top">
              <span className="request__kind">{KIND[r.kind] ?? r.kind} · No. {r.ref_id}</span>
              <span className="request__amt">{money(r.amount)}</span>
            </div>
            <div className="request__why">{r.reason}</div>
            <div className="request__meta">
              Prepared by {r.requested_by}{r.ticket_id ? ` for ticket ${r.ticket_id}` : ''} · request {r.id}
              {below && <b> · below the $200 floor; your call</b>}
            </div>
            {declining === r.id ? (
              <form className="request__decline" onSubmit={async e => {
                e.preventDefault(); if (!reason.trim()) return
                await onReject(r.id, reason.trim()); setDeclining(null); setReason('')
              }}>
                <input autoFocus value={reason} onChange={e => setReason(e.target.value)} placeholder="Reason for declining" />
                <button className="btn" type="submit">Decline</button>
                <button className="btn btn--ghost" type="button" onClick={() => setDeclining(null)}>Cancel</button>
              </form>
            ) : (
              <div className="request__actions">
                <button className="btn btn--primary" onClick={() => onApprove(r.id)}>Approve</button>
                <button className="btn btn--ghost" onClick={() => { setDeclining(r.id); setReason('') }}>Decline…</button>
              </div>
            )}
          </div>
        )
      })}
      {payments.length > 0 && (
        <div className="ledger">
          <h3>Paid</h3>
          {payments.map(p => (
            <div key={p.id} className="ledger__row">
              <span>{KIND[p.kind] ?? p.kind} No. {p.ref_id}</span>
              <span>{money(p.amount)}</span>
              <span className="ledger__by">signed {p.approved_by} · {p.paid_at}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
