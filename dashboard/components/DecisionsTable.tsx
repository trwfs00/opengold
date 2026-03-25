'use client'
import { DecisionRow } from '@/lib/api'

interface Props {
  decisions: DecisionRow[]
}

export default function DecisionsTable({ decisions }: Props) {
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          Decisions
        </h2>
        <span className="text-zinc-600 text-[10px] font-mono">{decisions.length} rows</span>
      </div>
      {decisions.length === 0 ? (
        <p className="text-zinc-600 text-sm font-mono">No decisions yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-zinc-600 text-left border-b border-zinc-800">
                <th className="pb-1.5 pr-3 font-medium">Time</th>
                <th className="pr-3 font-medium">Regime</th>
                <th className="pr-3 font-medium">Buy</th>
                <th className="pr-3 font-medium">Sell</th>
                <th className="pr-3 font-medium">Action</th>
                <th className="pr-3 font-medium">Conf.</th>
                <th className="font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((row, i) => (
                <tr key={i} className="border-t border-zinc-800/50 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/30 transition-colors">
                  <td className="py-1 pr-3 text-zinc-600">
                    {new Date(row.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
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
                  <td className="text-zinc-600 truncate max-w-32">{row.risk_block_reason ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
