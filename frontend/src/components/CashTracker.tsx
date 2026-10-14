// The live checking-balance tracker: balance, what is waiting, and the $200 floor.
import { useEffect, useRef, useState } from 'react'
import { money } from '../api'
import type { CashResponse } from '../types'

function useTween(target: number | null, ms = 700) {
  const [shown, setShown] = useState(target ?? 0)
  const from = useRef<number | null>(target)
  useEffect(() => {
    if (target == null) return
    // First value: show the real balance at once (never count up from $0).
    if (from.current == null) { from.current = target; setShown(target); return }
    const start = performance.now(), a = from.current
    let raf = 0
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / ms)
      setShown(a + (target - a) * (1 - Math.pow(1 - k, 3)))
      if (k < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return shown
}

export function CashTracker({ cash, history }: { cash: CashResponse | null; history: number[] }) {
  const balance = useTween(cash ? cash.checking_balance : null)
  if (!cash) return <div className="cash cash--loading">Opening the ledger…</div>
  const top = Math.max(...history, cash.checking_balance, 1)
  const after = cash.balance_after_pending
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / top) * 100))}%`
  const below = after < cash.cash_floor
  const points = history.map((v, i) => `${(i / Math.max(1, history.length - 1)) * 100},${30 - (v / top) * 28}`).join(' ')
  return (
    <div className="cash" aria-live="polite">
      <div className="cash__label">Checking · as of {cash.as_of}</div>
      <div className="cash__balance">{money(balance)}</div>
      <div className="gauge" title="Balance, the balance after waiting requests, and the $200 floor">
        <div className="gauge__bar" style={{ width: pct(cash.checking_balance) }} />
        <div className={`gauge__after${below ? ' gauge__after--low' : ''}`} style={{ width: pct(after) }} />
        <div className="gauge__floor" style={{ left: pct(cash.cash_floor) }}><span>Floor {money(cash.cash_floor)}</span></div>
      </div>
      <div className="cash__rows">
        <span>Awaiting signature</span><b>{money(cash.pending_requests_total)}</b>
        <span>If all are signed</span><b className={below ? 'warn' : ''}>{money(after)}</b>
      </div>
      {below && cash.pending_requests_total > 0 && (
        <div className="cash__note">Signing everything would cross the $200 floor; each decision is yours.</div>
      )}
      {cash.checking_balance < cash.cash_floor && cash.pending_requests_total === 0 && (
        <div className="cash__note">Checking is {money(cash.cash_floor - cash.checking_balance)} below the $200 floor.</div>
      )}
      {history.length > 1 && (
        <svg className="cash__spark" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden>
          <polyline points={points} />
        </svg>
      )}
    </div>
  )
}
