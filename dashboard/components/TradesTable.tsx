'use client'
import { TradeRow } from '@/lib/api'

interface Props {
  trades: TradeRow[]
}

export default function TradesTable({ trades }: Props) {
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          Trades
        </h2>
        <span className="text-zinc-600 text-[10px] font-mono">{trades.length} closed</span>
      </div>
      {trades.length === 0 ? (
        <p className="text-zinc-600 text-sm font-mono">No closed trades yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-zinc-600 text-left border-b border-zinc-800">
                <th className="pb-1.5 pr-3 font-medium">Closed</th>
                <th className="pr-3 font-medium">Dir</th>
                <th className="pr-3 font-medium">Lots</th>
                <th className="pr-3 font-medium">Open</th>
                <th className="pr-3 font-medium">Close</th>
                <th className="pr-3 font-medium text-right">P&amp;L</th>
                <th className="font-medium">Result</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((row, i) => (
                <tr key={i} className="border-t border-zinc-800/50 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/30 transition-colors">
                  <td className="py-1 pr-3 text-zinc-600">
                    {new Date(row.close_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className={`pr-3 font-semibold ${row.direction === 'BUY' ? 'text-amber-400' : 'text-red-400'}`}>
                    {row.direction}
                  </td>
                  <td className="pr-3 tabular-nums">{row.lot_size}</td>
                  <td className="pr-3 tabular-nums">{row.open_price.toFixed(2)}</td>
                  <td className="pr-3 tabular-nums">{row.close_price.toFixed(2)}</td>
                  <td className={`pr-3 font-semibold tabular-nums text-right ${row.pnl >= 0 ? 'text-amber-400' : 'text-red-400'}`}>
                    {row.pnl >= 0 ? '+' : ''}{row.pnl.toFixed(2)}
                  </td>
                  <td className={`font-semibold ${row.result === 'WIN' ? 'text-amber-400' : 'text-red-400'}`}>
                    {row.result}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
