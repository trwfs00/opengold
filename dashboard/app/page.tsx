'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useBot } from '@/context/BotContext'
import {
  fetchCandles, fetchAccount, fetchSignals,
  fetchTrades, fetchStats, fetchStatus, fetchSummary, postKillSwitch,
  CandleBar, AccountInfo, SignalsData, TradeRow, StatsData, StatusData, SummaryData,
} from '@/lib/api'
import StatusBar from '@/components/StatusBar'
import CandleChart from '@/components/CandleChart'
import HeroPanel from '@/components/HeroPanel'
import PerformancePanel from '@/components/PerformancePanel'
import SignalsPanel from '@/components/SignalsPanel'
import DecisionsTable from '@/components/DecisionsTable'
import TradesTable from '@/components/TradesTable'
import AnalyticsPanel from '@/components/AnalyticsPanel'
import ClaudeThought from '@/components/ClaudeThought'
import PositionEventsPanel from '@/components/PositionEventsPanel'

const POLL_MS = 5000

export default function Page() {
  const [candles, setCandles] = useState<CandleBar[]>([])
  const [account, setAccount] = useState<AccountInfo | null>(null)
  const [signals, setSignals] = useState<SignalsData | null>(null)
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [stats, setStats] = useState<StatsData | null>(null)
  const [status, setStatus] = useState<StatusData | null>(null)
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [isOnline, setIsOnline] = useState(true)
  const [fetchError, setFetchError] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)

  const { bot } = useBot()
  // Monotonic counter — each refresh() call gets a unique ID;
  // only the latest one commits results to state (prevents stale bot data)
  const runIdRef = useRef(0)

  // Reset all state when switching bots so stale data doesn't persist
  useEffect(() => {
    setCandles([])
    setAccount(null)
    setSignals(null)
    setTrades([])
    setStats(null)
    setStatus(null)
    setSummary(null)
    setIsInitialLoad(true)
    setFetchError(false)
  }, [bot])

  const refresh = useCallback(async () => {
    const runId = ++runIdRef.current

    const results = await Promise.allSettled([
      fetchCandles(bot),
      fetchAccount(bot),
      fetchSignals(bot),
      fetchTrades(bot),
      fetchStats(bot),
      fetchStatus(bot),
      fetchSummary(bot),
    ])

    // Discard results from a superseded fetch (bot switched or newer refresh ran)
    if (runIdRef.current !== runId) return

    const [r0, r1, r2, r3, r4, r5, r6] = results
    let anyError = false
    if (r0.status === 'fulfilled') setCandles(r0.value); else anyError = true
    if (r1.status === 'fulfilled') setAccount(r1.value); else anyError = true
    if (r2.status === 'fulfilled') setSignals(r2.value); else anyError = true
    if (r3.status === 'fulfilled') setTrades(r3.value); else anyError = true
    if (r4.status === 'fulfilled') setStats(r4.value); else anyError = true
    if (r5.status === 'fulfilled') setStatus(r5.value); else anyError = true
    if (r6.status === 'fulfilled') setSummary(r6.value); else anyError = true

    setFetchError(anyError)
    setIsInitialLoad(false)
  }, [bot])

  useEffect(() => {
    refresh()

    // Skip poll ticks while the tab is hidden — saves resources
    const id = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return
      refresh()
    }, POLL_MS)

    // Immediate refresh when the tab becomes visible again
    const handleVisibility = () => { if (!document.hidden) refresh() }
    // Track connectivity; refresh as soon as the connection comes back
    const handleOnline  = () => { setIsOnline(true);  refresh() }
    const handleOffline = () => setIsOnline(false)

    document.addEventListener('visibilitychange', handleVisibility)
    window.addEventListener('online',  handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', handleVisibility)
      window.removeEventListener('online',  handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [refresh])

  const handleKillSwitch = async (active: boolean) => {
    try {
      await postKillSwitch(bot, active)
      await fetchStatus(bot).then(setStatus)
    } catch {
      // ignore — status will be refreshed by next poll
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <StatusBar status={status} onKillSwitch={handleKillSwitch} />

      {/* Offline banner — shown whenever the browser loses network */}
      {!isOnline && (
        <div role="alert" className="bg-red-950/80 border-b border-red-800/60 px-4 py-1.5 text-center text-red-300 text-xs font-mono tracking-wide">
          No network connection — data may be stale
        </div>
      )}

      {/* Fetch error banner — only shown when online to avoid duplicating the offline message */}
      {fetchError && isOnline && (
        <div role="status" className="bg-amber-950/60 border-b border-amber-800/40 px-4 py-1.5 text-center text-amber-400/80 text-xs font-mono tracking-wide">
          Some API requests failed — retrying automatically
        </div>
      )}

      <main
        aria-busy={isInitialLoad}
        className={`max-w-screen-xl mx-auto transition-opacity duration-500 ${
          isInitialLoad ? 'opacity-30 pointer-events-none select-none' : 'opacity-100'
        }`}
      >
        {/* ── Market Context: price + chart ─────────────────────── */}
        {/* HeroPanel has its own px-3 sm:px-5 / pt-4 top padding */}
        <HeroPanel candles={candles} summary={summary} />

        <div className="px-2 sm:px-4 pb-12 sm:pb-16">

          {/* Chart — conceptually part of the market context group, tight gap */}
          <div className="mb-8 sm:mb-10">
            <CandleChart />
          </div>

          {/* ── Bot Performance ───────────────────────────────────── */}
          <div className="mb-8 sm:mb-10">
            <PerformancePanel stats={stats} account={account} />
          </div>

          {/* ── AI Signal Analysis ────────────────────────────────── */}
          {/* Three related components — tight intra-group spacing */}
          <div className="space-y-3 sm:space-y-4 mb-8 sm:mb-10">
            <SignalsPanel signals={signals} />
            <ClaudeThought />
            <AnalyticsPanel signals={signals} />
          </div>

          {/* ── Historical Records ────────────────────────────────── */}
          <div className="space-y-3 sm:space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
              <DecisionsTable />
              <TradesTable trades={trades} bot={bot} onRefresh={refresh} />
            </div>
            <PositionEventsPanel />
          </div>

        </div>
      </main>
    </div>
  )
}
