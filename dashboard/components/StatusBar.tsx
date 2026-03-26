'use client'
import { useState, useEffect } from 'react'
import { StatusData } from '@/lib/api'
import { useT } from '@/lib/i18n-context'
import BotTabSwitcher from '@/components/BotTabSwitcher'

interface Props {
  status: StatusData | null
  onKillSwitch: (active: boolean) => void
}

function ModelPricingTooltip({ modelName }: { modelName: string }) {
  const [open, setOpen] = useState(false)
  const { t } = useT()
  // token estimates based on prompt.py analysis
  const inputTokens = 350
  const outputTokens = 200
  const inputCostPer1M = 1.00
  const outputCostPer1M = 5.00
  const inputUSD = (inputTokens * inputCostPer1M) / 1_000_000
  const outputUSD = (outputTokens * outputCostPer1M) / 1_000_000
  const totalUSD = inputUSD + outputUSD
  const thbRate = 35
  const totalTHB = totalUSD * thbRate
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="text-zinc-600 hover:text-amber-400 transition-colors focus:outline-none"
        aria-label="AI model pricing"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 w-72 z-50 bg-zinc-950 border border-zinc-700/60 rounded-lg shadow-2xl shadow-black/60 p-3.5 text-[11px] font-mono">
          <p className="text-amber-400 font-semibold text-[10px] uppercase tracking-widest mb-2.5">{t.modelPricingTitle}</p>
          <p className="text-zinc-300 mb-2.5">{modelName}</p>
          <div className="space-y-1 text-zinc-400 mb-2.5">
            <div className="flex justify-between">
              <span>{t.modelPricingInput}</span>
              <span className="text-zinc-300">~{inputTokens} tokens × ${inputCostPer1M.toFixed(2)}/1M</span>
            </div>
            <div className="flex justify-between">
              <span>{t.modelPricingOutput}</span>
              <span className="text-zinc-300">~{outputTokens} tokens × ${outputCostPer1M.toFixed(2)}/1M</span>
            </div>
          </div>
          <div className="border-t border-zinc-800 pt-2.5 mb-2">
            <div className="flex justify-between items-baseline">
              <span className="text-zinc-400">{t.modelPricingCost}</span>
              <span className="text-amber-400 font-semibold">~${totalUSD.toFixed(4)} <span className="text-zinc-500">({totalTHB.toFixed(2)} ฿)</span></span>
            </div>
          </div>
          <p className="text-zinc-600 text-[9px]">{t.modelPricingBudget(10)}</p>
          <p className="text-zinc-700 text-[9px] mt-1">{t.modelPricingNote}</p>
        </div>
      )}
    </div>
  )
}

interface AiTimers {
  hotLeft: number    // seconds until HOT cooldown clears (60s)
  periodicLeft: number  // seconds until next PERIODIC call
}

function useAiTimers(lastAiTime?: string, intervalMinutes?: number): AiTimers | null {
  const [timers, setTimers] = useState<AiTimers | null>(null)

  useEffect(() => {
    if (!lastAiTime || !intervalMinutes) return
    const periodicTotal = intervalMinutes * 60
    const hotTotal = 60

    const calc = (): AiTimers => {
      const elapsed = (Date.now() - new Date(lastAiTime).getTime()) / 1000
      return {
        hotLeft: Math.max(0, Math.round(hotTotal - elapsed)),
        periodicLeft: Math.max(0, Math.round(periodicTotal - elapsed)),
      }
    }

    setTimers(calc())
    const id = setInterval(() => setTimers(calc()), 1000)
    return () => clearInterval(id)
  }, [lastAiTime, intervalMinutes])

  return timers
}

function fmtCountdown(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

export default function StatusBar({ status, onKillSwitch }: Props) {
  const { t, locale, setLocale } = useT()
  const timers = useAiTimers(status?.last_ai_time, status?.ai_interval_minutes)

  if (!status) {
    return (
      <div className="h-9 bg-zinc-900 border-b border-zinc-800 animate-pulse" />
    )
  }

  const alive = status.bot_alive
  const ksActive = status.kill_switch_active

  return (
    <div className="flex items-center justify-between px-5 h-9 bg-zinc-900 border-b border-zinc-800 text-xs font-mono">
      <div className="flex items-center gap-5">
        <BotTabSwitcher />
        <span className={`flex items-center gap-1.5 font-semibold tracking-wide ${alive ? 'text-lime-400' : 'text-red-400'}`}>
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${alive ? 'bg-lime-400 animate-pulse' : 'bg-red-400'}`} />
          {alive ? t.botAlive : t.botOffline}
        </span>
        {status.ai_model && (
          <span className="flex items-center gap-1 text-zinc-500">
            <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-60">
              <path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 6v6l4 2"/>
            </svg>
            <span className="text-[10px] tracking-wide">{status.ai_model}</span>
            <ModelPricingTooltip modelName={status.ai_model} />
          </span>
        )}
        {status.dry_run && (
          <span className="text-amber-500/70 border border-amber-500/30 px-1.5 py-0.5 rounded text-[10px] tracking-widest">
            {t.dryRun}
          </span>
        )}
        {timers !== null && (
          <span className="flex items-center gap-2.5 font-mono text-[10px]">
            {/* HOT cooldown — 60s */}
            <span className="flex items-center gap-1">
              <span className={`font-bold ${timers.hotLeft === 0 ? 'text-lime-400' : 'text-zinc-600'}`}>HOT</span>
              <span className={`tabular-nums ${timers.hotLeft === 0 ? 'text-lime-400' : 'text-zinc-500'}`}>
                {timers.hotLeft === 0 ? 'READY' : fmtCountdown(timers.hotLeft)}
              </span>
            </span>
            <span className="text-zinc-700">|</span>
            {/* PERIODIC — 5 min */}
            <span className="flex items-center gap-1">
              <span className={`font-bold ${timers.periodicLeft === 0 ? 'text-amber-400' : 'text-zinc-600'}`}>AI PERIOD</span>
              <span className={`tabular-nums ${
                timers.periodicLeft === 0 ? 'text-amber-400' :
                timers.periodicLeft <= 30 ? 'text-amber-500' : 'text-zinc-500'
              }`}>
                {timers.periodicLeft === 0 ? 'READY' : fmtCountdown(timers.periodicLeft)}
              </span>
            </span>
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {/* Language toggle */}
        <div className="flex items-center rounded overflow-hidden border border-zinc-700">
          <button
            onClick={() => setLocale('en')}
            className={`px-2 py-0.5 text-[10px] font-semibold tracking-wide transition-colors ${locale === 'en' ? 'bg-amber-500/20 text-amber-400' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            EN
          </button>
          <div className="w-px h-4 bg-zinc-700" />
          <button
            onClick={() => setLocale('th')}
            className={`px-2 py-0.5 text-[10px] font-semibold tracking-wide transition-colors ${locale === 'th' ? 'bg-amber-500/20 text-amber-400' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            TH
          </button>
        </div>
        <button
          onClick={() => onKillSwitch(!ksActive)}
          className={`px-3 py-1 rounded text-[11px] font-semibold tracking-wide transition-all ${
            ksActive
              ? 'bg-red-600 hover:bg-red-700 text-white ring-1 ring-red-500'
              : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700'
          }`}
        >
          {ksActive ? t.killSwitchActive : t.killSwitch}
        </button>
      </div>
    </div>
  )
}
