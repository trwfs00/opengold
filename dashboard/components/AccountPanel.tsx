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
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-zinc-600 text-left border-b border-zinc-800">
                  <th className="pb-1 pr-3 font-medium">Symbol</th>
                  <th className="pr-3 font-medium">Dir</th>
                  <th className="pr-3 font-medium">Lots</th>
                  <th className="font-medium text-right">P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {account.positions.map(p => (
                  <tr key={p.ticket} className="border-t border-zinc-800/60 text-zinc-300">
                    <td className="py-1 pr-3">{p.symbol}</td>
                    <td className={`pr-3 font-semibold ${p.direction === 'BUY' ? 'text-amber-400' : 'text-red-400'}`}>
                      {p.direction}
                    </td>
                    <td className="pr-3">{p.lots}</td>
                    <td className={`text-right font-semibold ${p.unrealized_pnl >= 0 ? 'text-amber-400' : 'text-red-400'}`}>
                      {p.unrealized_pnl >= 0 ? '+' : ''}{p.unrealized_pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
