'use client'
import { useCallback, useEffect, useState } from 'react'
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

const POLL_MS = 5000

export default function Page() {
  const [candles, setCandles] = useState<CandleBar[]>([])
  const [account, setAccount] = useState<AccountInfo | null>(null)
  const [signals, setSignals] = useState<SignalsData | null>(null)
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [stats, setStats] = useState<StatsData | null>(null)
  const [status, setStatus] = useState<StatusData | null>(null)
  const [summary, setSummary] = useState<SummaryData | null>(null)

  const { bot } = useBot()

  const refresh = useCallback(async () => {
    await Promise.allSettled([
      fetchCandles(bot).then(setCandles).catch(() => {}),
      fetchAccount(bot).then(setAccount).catch(() => {}),
      fetchSignals(bot).then(setSignals).catch(() => {}),
      fetchTrades(bot).then(setTrades).catch(() => {}),
      fetchStats(bot).then(setStats).catch(() => {}),
      fetchStatus(bot).then(setStatus).catch(() => {}),
      fetchSummary(bot).then(setSummary).catch(() => {}),
    ])
  }, [bot])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
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
      <main className="max-w-screen-xl mx-auto my-8 space-y-0">
        {/* Hero — price + countdown + summary stats */}
        <HeroPanel candles={candles} summary={summary} />

        <div className="px-4 space-y-4">
        {/* Chart — full width */}
        <CandleChart />

        {/* Performance — full width (merged stats + account) */}
        <PerformancePanel stats={stats} account={account} />

        {/* Signals */}
        <SignalsPanel signals={signals} />

        {/* Claude's latest reasoning */}
        <ClaudeThought />

        {/* Strategy analytics — breakdown bars + regime distribution */}
        <AnalyticsPanel signals={signals} />

        {/* Tables side by side */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <DecisionsTable />
          <TradesTable trades={trades} />
        </div>
        </div>
      </main>
    </div>
  )
}
