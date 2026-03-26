'use client'
import { AccountInfo } from '@/lib/api'

interface Props {
  account: AccountInfo | null
}

export default function AccountPanel({ account }: Props) {
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest mb-3">
        Account
      </h2>
      {!account || account.error ? (
        <p className="text-zinc-600 text-sm">{account?.error ?? 'Loading...'}</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Stat label="Balance" value={account.balance?.toFixed(2)} unit={account.currency ?? ''} />
            <Stat label="Equity" value={account.equity?.toFixed(2)} unit={account.currency ?? ''} />
            <Stat label="Open" value={String(account.positions?.length ?? 0)} unit="positions" />
          </div>
          {account.positions && account.positions.length > 0 && (
            <div className="space-y-2">
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest">Open Positions</p>
              {account.positions.map(p => {
                const isBuy = p.direction === 'BUY'
                const pnlPos = p.unrealized_pnl >= 0
                const pips = isBuy
                  ? (p.current_price - p.open_price).toFixed(2)
                  : (p.open_price - p.current_price).toFixed(2)
                const openedAt = p.open_time
                  ? new Date(p.open_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : '—'
                return (
                  <div
                    key={p.ticket}
                    className={`rounded border px-3 py-2.5 font-mono text-xs ${
                      isBuy ? 'border-amber-500/30 bg-amber-500/5' : 'border-red-500/30 bg-red-500/5'
                    }`}
                  >
                    {/* Top row: symbol + direction badge + P&L */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          isBuy ? 'bg-amber-500/20 text-amber-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {p.direction}
                        </span>
                        <span className="text-zinc-200 font-semibold">{p.symbol}</span>
                        <span className="text-zinc-500">{p.lots} lot</span>
                      </div>
                      <div className="text-right">
                        <span className={`font-semibold tabular-nums ${pnlPos ? 'text-amber-400' : 'text-red-400'}`}>
                          {pnlPos ? '+' : ''}{p.unrealized_pnl.toFixed(2)}
                        </span>
                        <span className="text-zinc-500 ml-1">USD</span>
                      </div>
                    </div>
                    {/* Price grid */}
                    <div className="grid grid-cols-4 gap-2 text-[10px]">
                      <div>
                        <p className="text-zinc-600 mb-0.5">Entry</p>
                        <p className="text-zinc-200 tabular-nums">{p.open_price.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-zinc-600 mb-0.5">Now</p>
                        <p className={`tabular-nums ${pnlPos ? 'text-amber-400' : 'text-red-400'}`}>
                          {p.current_price.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-zinc-600 mb-0.5">SL</p>
                        <p className="text-red-400/70 tabular-nums">{p.sl > 0 ? p.sl.toFixed(2) : '—'}</p>
                      </div>
                      <div>
                        <p className="text-zinc-600 mb-0.5">TP</p>
                        <p className="text-amber-400/70 tabular-nums">{p.tp > 0 ? p.tp.toFixed(2) : '—'}</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className="text-zinc-600 text-[10px]">Opened {openedAt}</span>
                      <span className={`text-[10px] tabular-nums ${pnlPos ? 'text-amber-500/60' : 'text-red-500/60'}`}>
                        {Number(pips) >= 0 ? '+' : ''}{pips} pts
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </section>
  )
}

function Stat({ label, value, unit }: { label: string; value?: string; unit: string }) {
  return (
    <div>
      <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-zinc-100 font-semibold tabular-nums">
        {value ?? '—'}
        {unit && <span className="text-zinc-500 text-xs ml-1">{unit}</span>}
      </p>
    </div>
  )
}
