'use client'
import { useCallback, useEffect, useState } from 'react'
import {
  fetchCandles, fetchAccount, fetchSignals, fetchDecisions,
  fetchTrades, fetchStats, fetchStatus, postKillSwitch,
  CandleBar, AccountInfo, SignalsData, DecisionRow, TradeRow, StatsData, StatusData,
} from '@/lib/api'
import StatusBar from '@/components/StatusBar'
import AccountPanel from '@/components/AccountPanel'
import CandleChart from '@/components/CandleChart'
import SignalsPanel from '@/components/SignalsPanel'
import DecisionsTable from '@/components/DecisionsTable'
import TradesTable from '@/components/TradesTable'
import StatsPanel from '@/components/StatsPanel'

const POLL_MS = 5000

export default function Page() {
  const [candles, setCandles] = useState<CandleBar[]>([])
  const [account, setAccount] = useState<AccountInfo | null>(null)
  const [signals, setSignals] = useState<SignalsData | null>(null)
  const [decisions, setDecisions] = useState<DecisionRow[]>([])
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [stats, setStats] = useState<StatsData | null>(null)
  const [status, setStatus] = useState<StatusData | null>(null)

  const refresh = useCallback(async () => {
    await Promise.allSettled([
      fetchCandles().then(setCandles).catch(() => {}),
      fetchAccount().then(setAccount).catch(() => {}),
      fetchSignals().then(setSignals).catch(() => {}),
      fetchDecisions().then(setDecisions).catch(() => {}),
      fetchTrades().then(setTrades).catch(() => {}),
      fetchStats().then(setStats).catch(() => {}),
      fetchStatus().then(setStatus).catch(() => {}),
    ])
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const handleKillSwitch = async (active: boolean) => {
    try {
      await postKillSwitch(active)
      await fetchStatus().then(setStatus)
    } catch {
      // ignore — status will be refreshed by next poll
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <StatusBar status={status} onKillSwitch={handleKillSwitch} />
      <main className="max-w-screen-2xl mx-auto p-4 space-y-4">
        {/* Chart — full width */}
        <CandleChart candles={candles} />

        {/* Signals + Account side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SignalsPanel signals={signals} />
          <AccountPanel account={account} />
        </div>

        {/* Stats — full width */}
        <StatsPanel stats={stats} />

        {/* Tables side by side */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <DecisionsTable decisions={decisions} />
          <TradesTable trades={trades} />
        </div>
      </main>
    </div>
  )
}
