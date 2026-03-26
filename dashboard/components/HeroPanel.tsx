'use client'
import { useEffect, useState } from 'react'
import { CandleBar, SummaryData } from '@/lib/api'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'
import { useT } from '@/lib/i18n-context'

interface Props {
  candles: CandleBar[]
  summary: SummaryData | null
}

function useCountdown() {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    function calc() {
      const now = new Date()
      const remaining = 60 - now.getSeconds()
      setSecs(remaining > 0 ? remaining : 60)
    }
    calc()
    const id = setInterval(calc, 500)
    return () => clearInterval(id)
  }, [])
  return { m: Math.floor(secs / 60), s: secs % 60 }
}

export default function HeroPanel({ candles, summary }: Props) {
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  const { m, s } = useCountdown()
  const latest = candles.at(-1)
  const prev = candles.at(-2)
  const price = latest?.close
  const change = price !== undefined && prev?.close !== undefined ? price - prev.close : null
  const changePct = change !== null && prev?.close ? (change / prev.close) * 100 : null
  const positive = change === null || change >= 0
  const decimals = bot === 'forex' ? 5 : 2

  return (
    <section className="px-5 pt-5 pb-8">
      {/* Top row: symbol + price | countdown */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <p className={`${meta.accent} text-[10px] font-mono font-semibold uppercase tracking-[0.2em] mb-1.5`}>
            {meta.symbol} {meta.label}
          </p>
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className={`${meta.accent} text-5xl font-mono font-bold tabular-nums tracking-tight leading-none`}>
              {price?.toFixed(decimals) ?? '—'}
            </span>
            {change !== null && changePct !== null && (
              <span className={`text-sm font-mono font-semibold tabular-nums ${positive ? 'text-lime-400' : 'text-red-400'}`}>
                {positive ? '+' : ''}{change.toFixed(decimals)} ({positive ? '+' : ''}{changePct.toFixed(2)}%)
              </span>
            )}
          </div>
          <p className="text-zinc-600 text-xs font-mono mt-2">
            {t.strategies}
          </p>
        </div>

        <div className="text-right shrink-0">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-1">
            {t.nextAnalysis}
          </p>
          <p className={`${meta.accentDim} font-mono text-3xl font-bold tabular-nums leading-none`}>
            {m}:{String(s).padStart(2, '0')}
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-stretch gap-0 divide-x divide-zinc-800/70">
        {/* TODAY W/L/H */}
        <div className="pr-6">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-1">{t.today}</p>
          <p className="font-mono text-sm font-semibold leading-snug">
            <span className={meta.accent}>{summary?.today_win ?? '—'}</span>
            <span className="text-zinc-700"> / </span>
            <span className="text-red-400">{summary?.today_loss ?? '—'}</span>
            <span className="text-zinc-700"> / </span>
            <span className="text-zinc-400">{summary?.today_hold ?? '—'}</span>
          </p>
          <p className="text-zinc-700 text-[9px] font-mono uppercase tracking-wider mt-0.5">{t.wlhLabel}</p>
        </div>

        {/* ALL-TIME */}
        <div className="px-6">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-1">{t.allTime}</p>
          <p className="text-zinc-100 font-mono text-sm font-semibold leading-snug">
            {summary?.all_time_decisions ?? '—'}
          </p>
          <p className="text-zinc-700 text-[9px] font-mono uppercase tracking-wider mt-0.5">{t.decisions}</p>
        </div>

        {/* DISCIPLINE */}
        <div className="px-6">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-1">{t.discipline}</p>
          <p className="text-zinc-100 font-mono text-sm font-semibold leading-snug">
            {summary?.discipline_hold_rate != null
              ? `${(summary.discipline_hold_rate * 100).toFixed(1)}%`
              : '—'}
          </p>
          <p className="text-zinc-700 text-[9px] font-mono uppercase tracking-wider mt-0.5">{t.holdRate}</p>
        </div>

        {/* CONFLUENCE */}
        <div className="pl-6">
          <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-widest mb-1">{t.confluence}</p>
          <p className="text-zinc-100 font-mono text-sm font-semibold leading-snug">
            {summary?.confluence_avg?.toFixed(1) ?? '—'}
          </p>
          <p className="text-zinc-700 text-[9px] font-mono uppercase tracking-wider mt-0.5">{t.avg}</p>
        </div>
      </div>
    </section>
  )
}
