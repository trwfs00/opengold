'use client'
import { useState, useEffect } from 'react'
import { TradeRow } from '@/lib/api'
import { useT } from '@/lib/i18n-context'

const PAGE_SIZE = 10

interface Props {
  trades: TradeRow[]
}

export default function TradesTable({ trades }: Props) {
  const { t } = useT()
  const [page, setPage] = useState(1)

  useEffect(() => { setPage(1) }, [trades.length])

  const totalPages = Math.max(1, Math.ceil(trades.length / PAGE_SIZE))
  const slice = trades.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          {t.tradesTitle}
        </h2>
        <span className="text-zinc-600 text-[10px] font-mono">{t.nClosed(trades.length)}</span>
      </div>
      {trades.length === 0 ? (
        <p className="text-zinc-600 text-sm font-mono">{t.noClosedTrades}</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-zinc-600 text-left border-b border-zinc-800">
                  <th className="pb-1.5 pr-3 font-medium">{t.colClosed}</th>
                  <th className="pr-3 font-medium">{t.colDir}</th>
                  <th className="pr-3 font-medium">{t.colLots}</th>
                  <th className="pr-3 font-medium">{t.colOpen}</th>
                  <th className="pr-3 font-medium">{t.colClose}</th>
                  <th className="pr-3 font-medium text-right">P&amp;L</th>
                  <th className="font-medium">{t.colResult}</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((row, i) => (
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
          {totalPages > 1 && (
            <div className="flex items-center justify-end gap-2 mt-3 pt-2 border-t border-zinc-800">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-2 py-0.5 text-[10px] font-mono text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                {t.prevPage}
              </button>
              <span className="text-[10px] font-mono text-zinc-600 tabular-nums">{t.pageOf(page, totalPages)}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-2 py-0.5 text-[10px] font-mono text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                {t.nextPage}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
