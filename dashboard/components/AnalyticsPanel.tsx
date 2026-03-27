'use client'
import { useEffect, useState } from 'react'
import { SignalsData, RegimeStats, fetchRegimeStats } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'

// Canonical display order of the 13 strategies
const STRATEGY_ORDER = [
  'ma_crossover',
  'rsi',
  'bollinger_bands',
  'macd',
  'support_resistance',
  'mean_reversion',
  'breakout',
  'momentum',
  'scalping',
  'vwap',
  'ichimoku',
  'stochastic',
  'trend_following',
]

// Human-readable labels
const STRATEGY_LABELS: Record<string, string> = {
  ma_crossover: 'MA Crossover',
  rsi: 'RSI',
  bollinger_bands: 'Bollinger Bands',
  macd: 'MACD',
  support_resistance: 'Support / Resistance',
  mean_reversion: 'Mean Reversion',
  breakout: 'Breakout',
  momentum: 'Momentum',
  scalping: 'Scalping',
  vwap: 'VWAP',
  ichimoku: 'Ichimoku',
  stochastic: 'Stochastic',
  trend_following: 'Trend Following (ADX)',
}

const REGIME_CONFIG: Record<string, { label: string; bar: string; text: string }> = {
  TRENDING_UP:   { label: 'Trending Up',   bar: 'bg-lime-500',    text: 'text-lime-400' },
  TRENDING_DOWN: { label: 'Trending Down', bar: 'bg-red-500',     text: 'text-red-400' },
  RANGING:       { label: 'Ranging',       bar: 'bg-sky-500',     text: 'text-sky-400' },
  TRANSITIONAL:  { label: 'Transitional',  bar: 'bg-zinc-500',    text: 'text-zinc-400' },
  BREAKOUT:      { label: 'Breakout',      bar: 'bg-amber-500',   text: 'text-amber-400' },
  // legacy key — kept for old DB rows
  TRENDING:      { label: 'Trending',      bar: 'bg-lime-400',    text: 'text-lime-300' },
}

interface Props {
  signals: SignalsData | null
}

export default function AnalyticsPanel({ signals }: Props) {
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  const [regimeStats, setRegimeStats] = useState<RegimeStats | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = () => fetchRegimeStats(bot).then(d => { if (!cancelled) setRegimeStats(d) }).catch(() => {})
    load()
    const id = setInterval(load, 15_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [bot])

  const signalMap = signals?.signals ?? null

  // Build ordered strategy list with fallback for unknown keys
  const strategyRows = STRATEGY_ORDER.map((key, idx) => {
    const entry = signalMap?.[key] ?? null
    return { key, idx, label: STRATEGY_LABELS[key] ?? key, entry }
  })

  // If there are extra keys not in canonical order, append them
  if (signalMap) {
    STRATEGY_ORDER.length // just reference to avoid ts warning
    const extra = Object.keys(signalMap).filter(k => !STRATEGY_ORDER.includes(k))
    extra.forEach((key, i) => {
      strategyRows.push({ key, idx: STRATEGY_ORDER.length + i, label: key, entry: signalMap[key] })
    })
  }

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest mb-4">
        {t.analyticsTitle}
      </h2>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* LEFT — Strategy breakdown */}
        <div>
          <p className="text-zinc-600 text-[9px] font-mono uppercase tracking-widest mb-3">
            {t.strategiesSection}
          </p>
          {!signalMap ? (
            <p className="text-zinc-600 text-sm font-mono">{t.noStrategyData}</p>
          ) : (
            <ol className="space-y-1.5">
              {strategyRows.map(({ key, idx, label, entry }) => {
                const isBuy = entry?.signal === 'BUY'
                const isSell = entry?.signal === 'SELL'
                const conf = entry?.confidence ?? 0
                const barColor = isBuy ? 'bg-amber-400' : isSell ? 'bg-red-400' : 'bg-zinc-600'
                const textColor = isBuy ? 'text-amber-400' : isSell ? 'text-red-400' : 'text-zinc-500'
                return (
                  <li key={key} className="flex items-center gap-2 font-mono text-[11px]">
                    <span className="text-zinc-600 w-4 shrink-0 text-right">{idx + 1}</span>
                    <span className="text-zinc-400 w-36 truncate shrink-0">{label}</span>
                    <span className={`w-12 shrink-0 text-right tabular-nums ${textColor}`}>
                      {entry ? `${(conf * 100).toFixed(0)}%` : '—'}
                    </span>
                    <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                        style={{ width: entry ? `${(conf * 100).toFixed(0)}%` : '0%' }}
                      />
                    </div>
                    <span className={`w-14 shrink-0 text-[10px] ${textColor}`}>
                      {entry?.signal ?? '—'}
                    </span>
                  </li>
                )
              })}
            </ol>
          )}
        </div>

        {/* RIGHT — Regime distribution + Under the Hood */}
        <div className="flex flex-col gap-5">
          {/* Regime distribution */}
          <div>
            <p className="text-zinc-600 text-[9px] font-mono uppercase tracking-widest mb-3">
              {t.regimeSection}
            </p>
            {!regimeStats || regimeStats.total === 0 ? (
              <p className="text-zinc-600 text-sm font-mono">{t.noRegimeData}</p>
            ) : (
              <>
                <div className="space-y-2">
                  {Object.entries(regimeStats.stats)
                    .sort((a, b) => b[1].pct - a[1].pct)
                    .map(([regime, data]) => {
                      const cfg = REGIME_CONFIG[regime] ?? { label: regime, bar: 'bg-zinc-500', text: 'text-zinc-400' }
                      return (
                        <div key={regime} className="flex items-center gap-2 font-mono text-[11px]">
                          <span className={`w-24 shrink-0 ${cfg.text}`}>{cfg.label}</span>
                          <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-700 ${cfg.bar}`}
                              style={{ width: `${data.pct}%` }}
                            />
                          </div>
                          <span className="text-zinc-400 w-10 text-right tabular-nums">{data.pct}%</span>
                        </div>
                      )
                    })}
                </div>
                <p className="text-zinc-700 text-[10px] font-mono mt-2">
                  {t.totalDecisions(regimeStats.total)}
                </p>
              </>
            )}
          </div>

          {/* Under the Hood */}
          <div>
            <p className="text-zinc-600 text-[9px] font-mono uppercase tracking-widest mb-3">
              {t.underTheHoodSection}
            </p>
            <ul className="space-y-1.5">
              {t.underTheHoodLines(meta.timeframe, meta.intervalMin).map((line, i) => {
                const prefix = line.slice(0, 1)
                const rest = line.slice(3)
                return (
                  <li key={i} className="flex gap-2 font-mono text-[11px]">
                    <span className={`${meta.accentDim} font-bold shrink-0`}>{prefix}</span>
                    <span className="text-zinc-500">{rest}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
