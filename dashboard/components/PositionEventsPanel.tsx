'use client'
import { useState, useEffect, useCallback } from 'react'
import { fetchPositionEvents, PositionEventRow } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'

const EVENT_CONFIG: Record<string, { label: (t: ReturnType<typeof useT>['t']) => string; color: string }> = {
  TRAIL_BE:     { label: t => t.posEventsTrailBE,       color: 'text-amber-400' },
  TRAIL_SL:     { label: t => t.posEventsTrailSL,       color: 'text-sky-400' },
  REEVAL_HOLD:  { label: t => t.posEventsReevalHold,    color: 'text-zinc-400' },
  PARTIAL_CLOSE:{ label: t => t.posEventsPartialClose,  color: 'text-orange-400' },
  REEVAL_CLOSE: { label: t => t.posEventsReevalClose,   color: 'text-red-400' },
}

function EventBadge({ type, t }: { type: string; t: ReturnType<typeof useT>['t'] }) {
  const cfg = EVENT_CONFIG[type] ?? { label: () => type, color: 'text-zinc-500' }
  return (
    <span className={`font-semibold tabular-nums ${cfg.color}`}>
      {cfg.label(t)}
    </span>
  )
}

export default function PositionEventsPanel() {
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  const [events, setEvents] = useState<PositionEventRow[]>([])

  const load = useCallback(async () => {
    try {
      const data = await fetchPositionEvents(bot, 200)
      setEvents(data)
    } catch {
      // keep existing on error
    }
  }, [bot])

  useEffect(() => {
    setEvents([])
    load()
  }, [bot, load])

  useEffect(() => {
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [load])

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
          {t.posEventsTitle}
        </h2>
        <span className="text-zinc-700 text-[10px] font-mono ml-auto">{events.length} rows</span>
      </div>

      {events.length === 0 ? (
        <p className="text-zinc-600 text-sm font-mono">{t.posEventsEmpty}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-zinc-600 text-left border-b border-zinc-800">
                <th className="pb-1.5 pr-3 font-medium">{t.colTime}</th>
                <th className="pr-3 font-medium">{t.posEventsTicket}</th>
                <th className="pr-3 font-medium">{t.colDir}</th>
                <th className="pr-3 font-medium">{t.posEventsEvent}</th>
                <th className="pr-3 font-medium">{t.posEventsPrice}</th>
                <th className="pr-3 font-medium">{t.posEventsOldSL}</th>
                <th className="pr-3 font-medium">{t.posEventsNewSL}</th>
                <th className="font-medium">{t.posEventsReason}</th>
              </tr>
            </thead>
            <tbody>
              {events.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-zinc-800/50 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/30 transition-colors"
                >
                  <td className="py-1 pr-3 text-zinc-600 whitespace-nowrap">
                    {new Date(row.time).toLocaleString([], {
                      month: '2-digit', day: '2-digit',
                      hour: '2-digit', minute: '2-digit', second: '2-digit',
                    })}
                  </td>
                  <td className={`pr-3 tabular-nums ${meta.accent}`}>{row.ticket}</td>
                  <td className={`pr-3 font-semibold ${
                    row.direction === 'BUY' ? 'text-amber-400' : 'text-red-400'
                  }`}>
                    {row.direction ?? '—'}
                  </td>
                  <td className="pr-3">
                    <EventBadge type={row.event_type} t={t} />
                  </td>
                  <td className="pr-3 tabular-nums text-zinc-300">
                    {row.price != null ? row.price.toFixed(5) : '—'}
                  </td>
                  <td className="pr-3 tabular-nums text-zinc-500">
                    {row.old_sl != null ? row.old_sl.toFixed(5) : '—'}
                  </td>
                  <td className={`pr-3 tabular-nums ${
                    row.new_sl != null ? 'text-zinc-200' : 'text-zinc-600'
                  }`}>
                    {row.new_sl != null ? row.new_sl.toFixed(5) : '—'}
                  </td>
                  <td className="text-zinc-500 font-mono text-[10px] max-w-xs">
                    {row.reasoning
                      ? <span className="italic text-zinc-400">{row.reasoning}</span>
                      : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
