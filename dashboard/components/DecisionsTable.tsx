'use client'
import { useState, useEffect, useCallback } from 'react'
import { fetchDecisions, DecisionRow } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import { useBot } from '@/context/BotContext'

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const

function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | '...')[] = [1]
  if (current > 3) pages.push('...')
  const lo = Math.max(2, current - 1)
  const hi = Math.min(total - 1, current + 1)
  for (let p = lo; p <= hi; p++) pages.push(p)
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
}

export default function DecisionsTable() {
  const { t } = useT()
  const { bot } = useBot()
  const [decisions, setDecisions] = useState<DecisionRow[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await fetchDecisions(bot, {
        limit: 10000,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
      setDecisions(data)
    } catch {
      // keep existing data on error
    }
  }, [dateFrom, dateTo, bot])

  useEffect(() => {
    setPage(1)
    load()
  }, [load])

  useEffect(() => {
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  const totalPages = Math.max(1, Math.ceil(decisions.length / pageSize))
  const slice = decisions.slice((page - 1) * pageSize, page * pageSize)
  const pageNumbers = getPageNumbers(page, totalPages)

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          {t.decisionsTitle}
        </h2>
        <span className="text-zinc-700 text-[10px] font-mono mr-auto">{t.rows(decisions.length)}</span>
        <input
          type="date"
          value={dateFrom}
          onChange={e => { setDateFrom(e.target.value); setPage(1) }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-400 text-[10px] font-mono px-2 py-0.5 rounded focus:outline-none focus:border-amber-500/50 [color-scheme:dark]"
        />
        <span className="text-zinc-600 text-[10px] font-mono">—</span>
        <input
          type="date"
          value={dateTo}
          onChange={e => { setDateTo(e.target.value); setPage(1) }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-400 text-[10px] font-mono px-2 py-0.5 rounded focus:outline-none focus:border-amber-500/50 [color-scheme:dark]"
        />
        <select
          value={pageSize}
          onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-400 text-[10px] font-mono px-1.5 py-0.5 rounded focus:outline-none focus:border-amber-500/50"
        >
          {PAGE_SIZE_OPTIONS.map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>

      {decisions.length === 0 ? (
        <p className="text-zinc-600 text-sm font-mono">{t.noDecisions}</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-zinc-600 text-left border-b border-zinc-800">
                  <th className="pb-1.5 pr-3 font-medium">{t.colTime}</th>
                  <th className="pr-3 font-medium">{t.colRegime}</th>
                  <th className="pr-3 font-medium">{t.colBuy}</th>
                  <th className="pr-3 font-medium">{t.colSell}</th>
                  <th className="pr-3 font-medium">{t.colAction}</th>
                  <th className="pr-3 font-medium">{t.colConf}</th>
                  <th className="font-medium">{t.colReason}</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((row, i) => (
                  <tr key={i} className="border-t border-zinc-800/50 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/30 transition-colors">
                    <td className="py-1 pr-3 text-zinc-600 whitespace-nowrap">
                      {new Date(row.time).toLocaleString([], {
                        month: '2-digit', day: '2-digit',
                        hour: '2-digit', minute: '2-digit', second: '2-digit',
                      })}
                    </td>
                    <td className="pr-3 text-zinc-300">{row.regime ?? '—'}</td>
                    <td className="pr-3 text-amber-400 tabular-nums">{row.buy_score?.toFixed(1) ?? '—'}</td>
                    <td className="pr-3 text-red-400 tabular-nums">{row.sell_score?.toFixed(1) ?? '—'}</td>
                    <td className={`pr-3 font-semibold ${
                      row.ai_action === 'BUY' ? 'text-amber-400' :
                      row.ai_action === 'SELL' ? 'text-red-400' :
                      'text-zinc-500'
                    }`}>
                      {row.ai_action ?? '—'}
                    </td>
                    <td className="pr-3 tabular-nums">
                      {row.ai_confidence != null ? `${(row.ai_confidence * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td className="text-zinc-500 font-mono text-[10px] max-w-xs">
                      {row.ai_reasoning
                        ? <span className="italic text-zinc-400">{row.ai_reasoning}</span>
                        : row.risk_block_reason
                        ? <span className="text-zinc-600">{row.risk_block_reason}</span>
                        : null
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-end gap-1 mt-3 pt-2 border-t border-zinc-800">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-2 py-0.5 text-[13px] leading-none font-mono text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                ‹
              </button>
              {pageNumbers.map((p, i) =>
                p === '...'
                  ? <span key={`e${i}`} className="px-1 text-[10px] font-mono text-zinc-700">…</span>
                  : <button
                      key={p}
                      onClick={() => setPage(p as number)}
                      className={`min-w-[22px] px-1.5 py-0.5 text-[10px] font-mono rounded transition-colors ${
                        page === p ? 'bg-amber-500/20 text-amber-400' : 'text-zinc-500 hover:text-zinc-200'
                      }`}
                    >{p}</button>
              )}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-2 py-0.5 text-[13px] leading-none font-mono text-zinc-500 hover:text-zinc-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                ›
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
