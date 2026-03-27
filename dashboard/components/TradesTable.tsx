"use client"
import { useState, useEffect } from "react"
import { TradeRow } from "@/lib/api"
import { postSyncTrades } from "@/lib/api"
import { useT } from "@/lib/i18n-context"

const PAGE_SIZE = 10

interface Props {
  trades: TradeRow[]
  bot: "gold" | "forex"
  onRefresh?: () => void
}

export default function TradesTable({ trades, bot, onRefresh }: Props) {
  const { t } = useT()
  const [page, setPage] = useState(1)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)

  useEffect(() => {
    setPage(1)
  }, [trades.length])

  const handleSync = async () => {
    setSyncing(true)
    setSyncMsg(null)
    try {
      const { synced } = await postSyncTrades(bot)
      setSyncMsg(t.syncDone(synced))
      onRefresh?.()
    } catch {
      setSyncMsg(t.syncFail)
    } finally {
      setSyncing(false)
      setTimeout(() => setSyncMsg(null), 4000)
    }
  }

  const totalPages = Math.max(1, Math.ceil(trades.length / PAGE_SIZE))
  const slice = trades.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const decimal = bot === "gold" ? 2 : 5

  return (
    <section className='bg-zinc-900 border border-zinc-800 rounded p-4'>
      <div className='flex items-center justify-between mb-3'>
        <h2 className='text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest'>
          {t.tradesTitle}
        </h2>
        <div className='flex items-center gap-2'>
          {syncMsg && (
            <span
              className={`text-[10px] font-mono tabular-nums ${
                syncMsg === t.syncFail ? "text-red-400" : "text-amber-400"
              }`}
            >
              {syncMsg}
            </span>
          )}
          <button
            onClick={handleSync}
            disabled={syncing}
            className='flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono text-zinc-400 hover:text-amber-400 border border-zinc-700 hover:border-amber-500/50 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed'
          >
            {syncing ? (
              <svg
                className='animate-spin h-3 w-3'
                viewBox='0 0 24 24'
                fill='none'
              >
                <circle
                  className='opacity-25'
                  cx='12'
                  cy='12'
                  r='10'
                  stroke='currentColor'
                  strokeWidth='4'
                />
                <path
                  className='opacity-75'
                  fill='currentColor'
                  d='M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z'
                />
              </svg>
            ) : (
              <svg
                className='h-3 w-3'
                viewBox='0 0 24 24'
                fill='none'
                stroke='currentColor'
                strokeWidth='2.5'
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  d='M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15'
                />
              </svg>
            )}
            {t.syncBtn}
          </button>
          <span className='text-zinc-600 text-[10px] font-mono'>
            {t.nClosed(trades.length)}
          </span>
        </div>
      </div>
      {trades.length === 0 ? (
        <p className='text-zinc-600 text-sm font-mono'>{t.noClosedTrades}</p>
      ) : (
        <>
          <div className='overflow-x-auto'>
            <table className='w-full text-xs font-mono'>
              <thead>
                <tr className='text-zinc-600 text-left border-b border-zinc-800'>
                  <th className='pb-1.5 pr-3 font-medium'>{t.colClosed}</th>
                  <th className='pr-3 font-medium'>{t.colDir}</th>
                  <th className='pr-3 font-medium'>{t.colLots}</th>
                  <th className='pr-3 font-medium'>{t.colOpen}</th>
                  <th className='pr-3 font-medium'>{t.colClose}</th>
                  <th className='pr-3 font-medium text-right'>P&amp;L</th>
                  <th className='font-medium'>{t.colResult}</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((row, i) => (
                  <tr
                    key={i}
                    className='border-t border-zinc-800/50 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/30 transition-colors'
                  >
                    <td className='py-1 pr-3 text-zinc-600'>
                      {new Date(row.close_time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td
                      className={`pr-3 font-semibold ${row.direction === "BUY" ? "text-amber-400" : "text-red-400"}`}
                    >
                      {row.direction}
                    </td>
                    <td className='pr-3 tabular-nums'>{row.lot_size}</td>
                    <td className='pr-3 tabular-nums'>
                      {row.open_price.toFixed(decimal)}
                    </td>
                    <td className='pr-3 tabular-nums'>
                      {row.close_price.toFixed(decimal)}
                    </td>
                    <td
                      className={`pr-3 font-semibold tabular-nums text-right ${row.pnl >= 0 ? "text-amber-400" : "text-red-400"}`}
                    >
                      {row.pnl >= 0 ? "+" : ""}
                      {row.pnl.toFixed(decimal)}
                    </td>
                    <td
                      className={`font-semibold ${row.result === "WIN" ? "text-amber-400" : "text-red-400"}`}
                    >
                      {row.result}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className='flex items-center justify-end gap-2 mt-3 pt-2 border-t border-zinc-800'>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className='px-2 py-0.5 text-[10px] font-mono text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors'
              >
                {t.prevPage}
              </button>
              <span className='text-[10px] font-mono text-zinc-600 tabular-nums'>
                {t.pageOf(page, totalPages)}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className='px-2 py-0.5 text-[10px] font-mono text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors'
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
