'use client'
import { useState } from 'react'
import { SignalsData } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'

interface Props {
  signals: SignalsData | null
}

function InfoTooltip() {
  const [open, setOpen] = useState(false)
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        onBlur={() => setOpen(false)}
        className={`text-zinc-600 ${meta.accentHover} transition-colors focus:outline-none`}
        aria-label="How decisions are made"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 w-80 z-50 bg-zinc-950 border border-zinc-700/60 rounded-lg shadow-2xl shadow-black/60 p-4 text-[11px] font-mono">
          <p className={`${meta.accent} font-semibold text-[10px] uppercase tracking-widest mb-3`}>{t.decisionPipeline}</p>
          <ol className="space-y-2.5 text-zinc-400 list-none">
            {t.pipelineSteps.map((step, i) => (
              <li key={i} className="flex gap-2">
                <span className={`${meta.accentDim} font-bold shrink-0`}>{i + 1}.</span>
                <span><span className="text-zinc-200">{step.label}</span> {step.desc}</span>
              </li>
            ))}
          </ol>
          <div className="mt-3 pt-3 border-t border-zinc-800 flex gap-4">
            <div>
              <p className="text-zinc-600 text-[9px] uppercase tracking-widest mb-0.5">{t.triggerThreshold}</p>
              <p className={meta.accent}>&ge; 4.0 score</p>
            </div>
            <div>
              <p className="text-zinc-600 text-[9px] uppercase tracking-widest mb-0.5">{t.minSeparation}</p>
              <p className={meta.accent}>&ge; 1.0 diff</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function SignalsPanel({ signals }: Props) {
  const { t } = useT()
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest mb-3">
        {t.signals}
      </h2>
      {!signals ? (
        <p className="text-zinc-600 text-sm animate-pulse">{t.loading}</p>
      ) : signals.error ? (
        <p className="text-red-400 text-sm font-mono">{signals.error}</p>
      ) : (
        <>
          {/* Regime + score row */}
          <div className="flex items-end gap-6 mb-4">
            <div>
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">{t.regime}</p>
              <div className="flex items-center gap-1.5">
                <p className="text-zinc-100 font-semibold tracking-wide">{signals.regime ?? '—'}</p>
                <InfoTooltip />
              </div>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">{t.buyScore}</p>
              <p className="text-amber-400 font-semibold font-mono tabular-nums">
                {signals.buy_score?.toFixed(2) ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">{t.sellScore}</p>
              <p className="text-red-400 font-semibold font-mono tabular-nums">
                {signals.sell_score?.toFixed(2) ?? '—'}
              </p>
            </div>
            {!signals.connected && (
              <span className="text-amber-500/60 text-[10px] font-mono border border-amber-500/20 px-1.5 py-0.5 rounded ml-auto">
                {t.mt5Disconnected}
              </span>
            )}
          </div>

          {signals.message && !signals.signals && (
            <p className="text-zinc-600 text-sm font-mono">{signals.message}</p>
          )}

          {/* Per-strategy signal cards */}
          {signals.signals && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(signals.signals).map(([name, data]) => {
                const isBuy = data.signal === 'BUY'
                const isSell = data.signal === 'SELL'
                return (
                  <div
                    key={name}
                    className={`rounded border px-3 py-2 text-xs font-mono ${
                      isBuy ? 'border-amber-500/30 bg-amber-500/5' :
                      isSell ? 'border-red-500/30 bg-red-500/5' :
                      'border-zinc-700 bg-zinc-800/40'
                    }`}
                  >
                    <p className="text-zinc-500 mb-1 truncate">{name}</p>
                    <div className="flex items-baseline justify-between">
                      <span className={`font-semibold tracking-wide ${
                        isBuy ? 'text-amber-400' : isSell ? 'text-red-400' : 'text-zinc-400'
                      }`}>
                        {data.signal}
                      </span>
                      <span className="text-zinc-500">{(data.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </section>
  )
}
