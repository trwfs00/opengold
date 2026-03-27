'use client'
import { useEffect, useRef } from 'react'
import { StatsData } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function dedupAsc(data: any[]) {
  return data.filter((d: any, i: number) => i === 0 || d.time > data[i - 1].time)
}

type Grade = 'A' | 'B' | 'C' | 'D' | 'F' | '?'

function computeGrade(stats: StatsData): Grade {
  if ((stats.total_trades ?? 0) < 10) return '?'
  const wr = stats.win_rate ?? 0
  const pf = stats.profit_factor ?? 0
  const exp = stats.expectancy ?? -Infinity
  if (pf >= 1.5 && wr >= 0.5 && exp > 0) return 'A'
  if (pf >= 1.3 && wr >= 0.45 && exp > 0) return 'B'
  if (pf >= 1.0 && exp > 0) return 'C'
  if (pf >= 0.8 || exp > -5) return 'D'
  return 'F'
}

const GRADE_STYLE: Record<Grade, { text: string; bg: string; border: string }> = {
  A:  { text: 'text-lime-400',   bg: 'bg-lime-500/10',   border: 'border-lime-500/40' },
  B:  { text: 'text-emerald-400',bg: 'bg-emerald-500/10',border: 'border-emerald-500/40' },
  C:  { text: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/40' },
  D:  { text: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/40' },
  F:  { text: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/40' },
  '?':{ text: 'text-zinc-500',   bg: 'bg-zinc-800',      border: 'border-zinc-700' },
}

interface Props {
  stats: StatsData | null
  open: boolean
  onClose: () => void
}

export default function PerformanceSummaryModal({ stats, open, onClose }: Props) {
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  const chartContainerRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null)

  // Mount chart when modal opens
  useEffect(() => {
    if (!open || !chartContainerRef.current || !stats?.pnl_curve?.length) return
    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
      const chart = createChart(chartContainerRef.current!, {
        layout: { background: { type: ColorType.Solid, color: '#18181b' }, textColor: '#71717a' },
        grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
        width: chartContainerRef.current!.clientWidth,
        height: 200,
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#27272a' },
        rightPriceScale: { borderColor: '#27272a' },
        crosshair: { mode: 1 },
      })
      const series = chart.addLineSeries({
        color: meta.hex,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
      })
      series.setData(dedupAsc(stats.pnl_curve))
      chart.timeScale().fitContent()
      chartRef.current = chart
    })
    return () => {
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null }
    }
  }, [open, bot, stats?.pnl_curve, meta.hex])

  if (!open) return null

  const grade = stats ? computeGrade(stats) : '?'
  const gs = GRADE_STYLE[grade]

  const gradeDesc: Record<Grade, string> = {
    A: t.perfGradeA, B: t.perfGradeB, C: t.perfGradeC,
    D: t.perfGradeD, F: t.perfGradeF, '?': t.perfGradeNA,
  }

  // Build analysis bullets
  const bullets: { text: string; positive: boolean }[] = []
  if (stats) {
    const total = stats.total_trades ?? 0
    const wr = stats.win_rate
    const pf = stats.profit_factor
    const exp = stats.expectancy
    const dd = stats.max_drawdown

    if (wr != null)
      bullets.push({
        text: t.perfBulletWR(`${(wr * 100).toFixed(1)}`, wr >= 0.5),
        positive: wr >= 0.5,
      })
    if (pf != null)
      bullets.push({
        text: t.perfBulletPF(
          pf.toFixed(2),
          pf >= 1.5 ? 'great' : pf >= 1.0 ? 'ok' : 'bad'
        ),
        positive: pf >= 1.0,
      })
    if (exp != null)
      bullets.push({
        text: t.perfBulletExp(Math.abs(exp).toFixed(2), exp >= 0),
        positive: exp >= 0,
      })
    if (dd != null)
      bullets.push({
        text: t.perfBulletDD(dd.toFixed(2), dd >= 50),
        positive: dd < 50,
      })
    bullets.push({
      text: t.perfBulletCount(total),
      positive: total >= 30,
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-full max-w-lg bg-zinc-900 border border-zinc-700/60 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className={`flex items-center justify-between px-5 py-4 border-b border-zinc-800/80 ${meta.accentBg} shrink-0`}>
          <div>
            <p className={`${meta.accent} text-[10px] font-mono font-bold uppercase tracking-[0.2em]`}>
              {t.perfModalTitle}
            </p>
            <p className="text-zinc-500 text-[11px] font-mono mt-0.5">
              {meta.symbol} · {meta.label}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-600 hover:text-zinc-300 transition-colors w-6 h-6 flex items-center justify-center text-sm"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-5">

          {/* Equity Curve chart */}
          {stats?.pnl_curve?.length ? (
            <div>
              <p className="text-zinc-600 text-[9px] font-mono uppercase tracking-[0.18em] mb-2">
                Cumulative P&amp;L
              </p>
              <div ref={chartContainerRef} className="rounded-lg overflow-hidden" />
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-800/50 px-4 py-8 text-center">
              <p className="text-zinc-600 text-[11px] font-mono">{t.perfNoCurve}</p>
            </div>
          )}

          {/* Grade card */}
          {stats && (
            <div className={`rounded-xl border ${gs.border} ${gs.bg} px-4 py-3 flex items-center gap-4`}>
              <span className={`${gs.text} text-4xl font-mono font-bold tabular-nums leading-none shrink-0`}>
                {grade}
              </span>
              <div>
                <p className="text-zinc-500 text-[9px] font-mono uppercase tracking-[0.18em] mb-0.5">
                  {t.perfGradeLabel}
                </p>
                <p className={`${gs.text} text-sm font-mono font-semibold`}>
                  {gradeDesc[grade]}
                </p>
              </div>
            </div>
          )}

          {/* Analysis bullets */}
          {bullets.length > 0 && (
            <div>
              <p className="text-zinc-600 text-[9px] font-mono uppercase tracking-[0.18em] mb-2.5">
                {t.perfAnalysis}
              </p>
              <ul className="space-y-2">
                {bullets.map((b, i) => (
                  <li key={i} className="flex items-start gap-2.5 font-mono text-[12px] leading-relaxed">
                    <span className={`shrink-0 mt-0.5 text-[10px] ${b.positive ? 'text-lime-500' : 'text-red-500'}`}>
                      {b.positive ? '▲' : '▼'}
                    </span>
                    <span className="text-zinc-300">{b.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* No data fallback */}
          {!stats && (
            <p className="text-zinc-600 text-[11px] font-mono text-center py-4">
              {t.perfNoCurve}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
