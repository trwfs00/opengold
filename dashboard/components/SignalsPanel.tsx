'use client'
import { SignalsData } from '@/lib/api'

interface Props {
  signals: SignalsData | null
}

export default function SignalsPanel({ signals }: Props) {
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest mb-3">
        Signals
      </h2>
      {!signals ? (
        <p className="text-zinc-600 text-sm animate-pulse">Loading...</p>
      ) : signals.error ? (
        <p className="text-red-400 text-sm font-mono">{signals.error}</p>
      ) : (
        <>
          {/* Regime + score row */}
          <div className="flex items-end gap-6 mb-4">
            <div>
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">Regime</p>
              <p className="text-zinc-100 font-semibold tracking-wide">{signals.regime ?? '—'}</p>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">Buy Score</p>
              <p className="text-amber-400 font-semibold font-mono tabular-nums">
                {signals.buy_score?.toFixed(2) ?? '—'}
              </p>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-mono uppercase tracking-wider mb-0.5">Sell Score</p>
              <p className="text-red-400 font-semibold font-mono tabular-nums">
                {signals.sell_score?.toFixed(2) ?? '—'}
              </p>
            </div>
            {!signals.connected && (
              <span className="text-amber-500/60 text-[10px] font-mono border border-amber-500/20 px-1.5 py-0.5 rounded ml-auto">
                MT5 DISCONNECTED
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
