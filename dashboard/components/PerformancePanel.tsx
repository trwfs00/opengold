'use client'
import { useEffect, useRef } from 'react'
import { StatsData, AccountInfo } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'

interface Props {
  stats: StatsData | null
  account: AccountInfo | null
}

export default function PerformancePanel({ stats, account }: Props) {
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  const containerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const seriesRef = useRef<any>(null)

  useEffect(() => {
    if (!containerRef.current) return
    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (chartRef.current) chartRef.current.remove()
      const chart = createChart(containerRef.current!, {
        layout: { background: { type: ColorType.Solid, color: '#18181b' }, textColor: '#71717a' },
        grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
        width: containerRef.current!.clientWidth,
        height: 120,
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#27272a' },
        rightPriceScale: { borderColor: '#27272a' },
      })
      const series = chart.addLineSeries({ color: meta.hex, lineWidth: 2, priceLineVisible: false })
      chartRef.current = chart
      seriesRef.current = series
      if (stats?.pnl_curve?.length) {
        series.setData(stats.pnl_curve as any)
        chart.timeScale().fitContent()
      }
    })
    return () => {
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null; seriesRef.current = null }
    }
  }, [bot]) // recreate chart when bot changes

  useEffect(() => {
    if (seriesRef.current && stats?.pnl_curve?.length) {
      seriesRef.current.setData(stats.pnl_curve as any)
      chartRef.current?.timeScale().fitContent()
    }
  }, [stats?.pnl_curve])

  const streak = stats?.current_streak ?? 0
  const streakLabel = streak > 0 ? `${streak}W` : streak < 0 ? `${Math.abs(streak)}L` : '—'
  const streakColor = streak > 0 ? 'text-amber-400' : streak < 0 ? 'text-red-400' : 'text-zinc-500'
  const streakSub = streak > 0 ? t.winStreak : streak < 0 ? t.lossStreak : undefined
  const openCount = account?.positions?.length ?? 0

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          {t.performance}
        </h2>
        {account && !account.error && (
          <div className="flex items-center gap-5 text-[10px] font-mono text-zinc-500">
            <span>
              {t.balance}{' '}
              <span className="text-zinc-200 font-semibold tabular-nums">
                {account.balance?.toFixed(2)}
              </span>{' '}
              <span className="text-zinc-600">{account.currency}</span>
            </span>
            <span>
              {t.equity}{' '}
              <span className="text-zinc-200 font-semibold tabular-nums">
                {account.equity?.toFixed(2)}
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Stats ticker row */}
      <div className="flex items-stretch divide-x divide-zinc-800 mb-4">
        <StatTile
          label={t.winRate}
          value={stats?.win_rate != null ? `${(stats.win_rate * 100).toFixed(1)}%` : '—'}
          color={stats?.win_rate != null ? (stats.win_rate >= 0.5 ? 'text-amber-400' : 'text-red-400') : 'text-zinc-500'}
        />
        <WLTile wins={stats?.win_count ?? 0} losses={stats?.loss_count ?? 0} />
        <StatTile label={t.closed} value={stats?.total_trades != null ? String(stats.total_trades) : '—'} />
        <StatTile
          label={t.avgRR}
          value={stats?.avg_rr != null ? `${stats.avg_rr.toFixed(2)}:1` : '—'}
          color={stats?.avg_rr != null ? (stats.avg_rr >= 1 ? 'text-amber-400' : 'text-zinc-400') : 'text-zinc-500'}
        />
        <StatTile
          label={t.streak}
          value={streakLabel}
          color={streakColor}
          sublabel={streakSub}
        />
        <StatTile label={t.open} value={String(openCount)} />
        <StatTile
          label={t.totalPnL}
          value={stats?.total_pnl != null
            ? `${stats.total_pnl >= 0 ? '+' : ''}${stats.total_pnl.toFixed(2)}`
            : '—'}
          color={stats?.total_pnl != null
            ? (stats.total_pnl >= 0 ? 'text-amber-400' : 'text-red-400')
            : 'text-zinc-500'}
        />
      </div>

      {/* Last 15 trades */}
      {stats && stats.last_15.length > 0 && (
        <div className="mb-4">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-2">
            {t.lastNTrades(stats.last_15.length)}
          </p>
          <div className="flex gap-1">
            {stats.last_15.map((result, i) => (
              <div
                key={i}
                title={result}
                className={`w-5 h-5 rounded-sm ${
                  result === 'WIN' ? 'bg-amber-500/80' :
                  result === 'LOSS' ? 'bg-red-500/80' :
                  'bg-zinc-600'
                }`}
              />
            ))}
          </div>
        </div>
      )}

      {/* P&L curve chart */}
      {stats && stats.pnl_curve.length > 0 ? (
        <div ref={containerRef} className="mb-4" />
      ) : (
        <p className="text-zinc-600 text-xs font-mono mb-4">{t.noClosedTrades}</p>
      )}

      {/* Open positions (from AccountPanel) */}
      {account?.positions && account.positions.length > 0 && (
        <div className="border-t border-zinc-800 pt-4 space-y-2">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-2">{t.openPositions}</p>
          {account.positions.map(p => {
            const isBuy = p.direction === 'BUY'
            const pnlPos = p.unrealized_pnl >= 0
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
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      isBuy ? 'bg-amber-500/20 text-amber-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {p.direction}
                    </span>
                    <span className="text-zinc-200 font-semibold">{p.symbol}</span>
                    <span className="text-zinc-500">{p.lots} {t.lot}</span>
                  </div>
                  <div className="text-right">
                    <span className={`font-semibold tabular-nums ${pnlPos ? 'text-amber-400' : 'text-red-400'}`}>
                      {pnlPos ? '+' : ''}{p.unrealized_pnl.toFixed(2)}
                    </span>
                    <span className="text-zinc-500 ml-1">USD</span>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-[10px]">
                  <div><p className="text-zinc-600 mb-0.5">{t.entry}</p><p className="text-zinc-200 tabular-nums">{p.open_price.toFixed(2)}</p></div>
                  <div><p className="text-zinc-600 mb-0.5">{t.now}</p><p className={`tabular-nums ${pnlPos ? 'text-amber-400' : 'text-red-400'}`}>{p.current_price.toFixed(2)}</p></div>
                  <div><p className="text-zinc-600 mb-0.5">SL</p><p className="text-red-400/70 tabular-nums">{p.sl > 0 ? p.sl.toFixed(2) : '—'}</p></div>
                  <div><p className="text-zinc-600 mb-0.5">TP</p><p className="text-amber-400/70 tabular-nums">{p.tp > 0 ? p.tp.toFixed(2) : '—'}</p></div>
                </div>
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-zinc-600 text-[10px]">Opened {openedAt}</span>
                  <span className={`text-[10px] tabular-nums ${pnlPos ? 'text-amber-500/60' : 'text-red-500/60'}`}>
                    {(p.current_price - p.open_price >= 0 ? '+' : '')}{(p.current_price - p.open_price).toFixed(2)} pts
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

function StatTile({
  label, value, color = 'text-zinc-100', sublabel,
}: {
  label: string; value: string; color?: string; sublabel?: string
}) {
  return (
    <div className="flex-1 px-4 first:pl-0 last:pr-0">
      <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`font-semibold font-mono tabular-nums text-base ${color}`}>{value}</p>
      {sublabel && <p className="text-zinc-600 text-[9px] font-mono uppercase tracking-widest">{sublabel}</p>}
    </div>
  )
}

function WLTile({ wins, losses }: { wins: number; losses: number }) {
  return (
    <div className="flex-1 px-4">
      <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">W / L</p>
      <p className="font-mono tabular-nums text-base font-semibold">
        <span className="text-amber-400">{wins}</span>
        <span className="text-zinc-600 mx-1">/</span>
        <span className="text-red-400">{losses}</span>
      </p>
    </div>
  )
}
