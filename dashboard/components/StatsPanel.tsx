'use client'
import { useEffect, useRef } from 'react'
import { StatsData } from '@/lib/api'

interface Props {
  stats: StatsData | null
}

export default function StatsPanel({ stats }: Props) {
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
        layout: {
          background: { type: ColorType.Solid, color: '#18181b' },
          textColor: '#71717a',
        },
        grid: {
          vertLines: { color: '#27272a' },
          horzLines: { color: '#27272a' },
        },
        width: containerRef.current!.clientWidth,
        height: 140,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: '#27272a',
        },
        rightPriceScale: {
          borderColor: '#27272a',
        },
      })

      const series = chart.addLineSeries({
        color: '#f59e0b',   // amber
        lineWidth: 2,
        priceLineVisible: false,
      })

      chartRef.current = chart
      seriesRef.current = series

      if (stats?.pnl_curve?.length) {
        series.setData(stats.pnl_curve as any)
        chart.timeScale().fitContent()
      }
    })

    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        seriesRef.current = null
      }
    }
  }, []) // mount only

  useEffect(() => {
    if (seriesRef.current && stats?.pnl_curve?.length) {
      seriesRef.current.setData(stats.pnl_curve as any)
      chartRef.current?.timeScale().fitContent()
    }
  }, [stats?.pnl_curve])

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest mb-3">
        Statistics
      </h2>
      {!stats ? (
        <p className="text-zinc-600 text-sm font-mono animate-pulse">Loading...</p>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <StatItem
              label="Win Rate"
              value={stats.win_rate !== null ? `${(stats.win_rate * 100).toFixed(1)}%` : '—'}
            />
            <StatItem
              label="Total P&L"
              value={stats.total_pnl !== null ? `${stats.total_pnl >= 0 ? '+' : ''}${stats.total_pnl.toFixed(2)}` : '—'}
              color={stats.total_pnl >= 0 ? 'text-amber-400' : 'text-red-400'}
            />
            <StatItem
              label="Avg Win"
              value={stats.avg_win !== null ? `+${stats.avg_win.toFixed(2)}` : '—'}
              color="text-amber-400"
            />
            <StatItem
              label="Avg Loss"
              value={stats.avg_loss !== null ? stats.avg_loss.toFixed(2) : '—'}
              color="text-red-400"
            />
          </div>
          {stats.pnl_curve.length === 0 ? (
            <p className="text-zinc-600 text-sm font-mono">No trades yet.</p>
          ) : (
            <div ref={containerRef} />
          )}
        </>
      )}
    </section>
  )
}

function StatItem({ label, value, color = 'text-zinc-100' }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`font-semibold font-mono tabular-nums ${color}`}>{value}</p>
    </div>
  )
}
