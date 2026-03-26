'use client'
import { useEffect, useRef, useState } from 'react'
import { fetchDecisions, DecisionRow } from '@/lib/api'
import { useBot } from '@/context/BotContext'

function ActionBadge({ action, blockReason }: { action: string | null; blockReason: string | null }) {
  if (!action) return null
  if (action === 'SKIP' || blockReason) {
    return (
      <span className="text-[10px] font-mono font-semibold uppercase tracking-widest text-zinc-500 border border-zinc-700 px-2 py-0.5 rounded">
        {blockReason ?? 'SKIP'}
      </span>
    )
  }
  const isBuy = action === 'BUY'
  return (
    <span className={`text-[10px] font-mono font-semibold uppercase tracking-widest px-2 py-0.5 rounded border ${
      isBuy
        ? 'text-amber-400 border-amber-500/40 bg-amber-500/5'
        : 'text-red-400 border-red-500/40 bg-red-500/5'
    }`}>
      {action}
    </span>
  )
}

export default function ClaudeThought() {
  const [latest, setLatest] = useState<DecisionRow | null>(null)
  const [displayed, setDisplayed] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const prevReasoningRef = useRef<string | null>(null)
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { bot } = useBot()

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const data = await fetchDecisions(bot, { limit: 1 })
        if (!cancelled && data.length > 0) setLatest(data[0])
      } catch {}
    }
    load()
    const id = setInterval(load, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [bot])

  // Typewriter effect when reasoning changes
  useEffect(() => {
    const text = latest?.ai_reasoning ?? ''
    if (!text || text === prevReasoningRef.current) return
    prevReasoningRef.current = text

    if (typingTimerRef.current) clearTimeout(typingTimerRef.current)
    setDisplayed('')
    setIsTyping(true)

    let i = 0
    const step = () => {
      i++
      setDisplayed(text.slice(0, i))
      if (i < text.length) {
        typingTimerRef.current = setTimeout(step, 18)
      } else {
        setIsTyping(false)
      }
    }
    typingTimerRef.current = setTimeout(step, 18)
    return () => { if (typingTimerRef.current) clearTimeout(typingTimerRef.current) }
  }, [latest?.ai_reasoning])

  if (!latest) return null

  const reasoning = displayed || latest.ai_reasoning
  if (!reasoning) return null

  const time = latest.time
    ? new Date(latest.time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC'
    : null

  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded p-4">
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-zinc-500 text-[10px] font-mono font-semibold uppercase tracking-widest">
            Claude
          </span>
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${isTyping ? 'bg-amber-400 animate-pulse' : 'bg-zinc-700'}`} />
        </div>
        <div className="flex items-center gap-2">
          <ActionBadge action={latest.ai_action} blockReason={latest.risk_block_reason} />
          {time && (
            <span className="text-zinc-600 text-[10px] font-mono tabular-nums">{time}</span>
          )}
        </div>
      </div>

      {/* Reasoning text */}
      <blockquote className="border-l-2 border-zinc-700 pl-3">
        <p className="text-zinc-300 text-sm font-mono leading-relaxed">
          {reasoning}
          {isTyping && <span className="inline-block w-0.5 h-4 bg-amber-400 ml-0.5 animate-pulse align-middle" />}
        </p>
      </blockquote>

      {/* Score context */}
      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-zinc-800/60">
        <span className="text-zinc-600 text-[10px] font-mono">
          buy <span className="text-amber-500/70 tabular-nums">{latest.buy_score?.toFixed(2) ?? '—'}</span>
        </span>
        <span className="text-zinc-600 text-[10px] font-mono">
          sell <span className="text-red-500/70 tabular-nums">{latest.sell_score?.toFixed(2) ?? '—'}</span>
        </span>
        {latest.regime && (
          <span className="text-zinc-600 text-[10px] font-mono uppercase">
            {latest.regime}
          </span>
        )}
        {latest.ai_confidence != null && (
          <span className="text-zinc-600 text-[10px] font-mono ml-auto">
            conf <span className="text-zinc-400 tabular-nums">{(latest.ai_confidence * 100).toFixed(0)}%</span>
          </span>
        )}
      </div>
    </section>
  )
}
