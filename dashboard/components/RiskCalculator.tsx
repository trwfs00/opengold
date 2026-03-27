'use client'
import { useState, useMemo } from 'react'
import { useBot } from '@/context/BotContext'
import { BOT_META } from '@/lib/bot-meta'
import { useT } from '@/lib/i18n-context'

// ── Risk config (mirrors the .env files) ────────────────────────────────────
const RISK_CONFIG = {
  gold: {
    instrumentType: 'gold' as const,
    riskPerTrade: 0.002,   // 0.2%
    contractSize: 100,     // oz per lot
    slMin: 5,              // USD SL min
    slMid: 12,             // USD SL typical
    slMax: 20,             // USD SL max
  },
  forex: {
    instrumentType: 'forex' as const,
    riskPerTrade: 0.01,    // 1%
    contractSize: 100_000, // units per lot
    pipValuePerLot: 10,    // USD per pip per lot
    slMin: 1,              // pips SL min
    slMid: 13,             // pips SL typical
    slMax: 25,             // pips SL max
  },
} as const

const MIN_LOT = 0.01
const LOT_STEP = 0.01

const LEVERAGE_OPTIONS = [
  { label: '—', value: 0 },
  { label: '1:10', value: 10 },
  { label: '1:30', value: 30 },
  { label: '1:50', value: 50 },
  { label: '1:100', value: 100 },
  { label: '1:200', value: 200 },
  { label: '1:500', value: 500 },
  { label: '1:1000', value: 1000 },
  { label: '1:2000', value: 2000 },
  { label: '1:3000', value: 3000 },
]

const HIGH_LEVERAGE_THRESHOLD = 500

interface Scenario {
  label: string
  slLabel: string
  lot: number
  riskUsd: number
  marginUsd: number | null
  feasible: boolean
}

function floorLot(raw: number): number {
  return Math.floor(raw / LOT_STEP) * LOT_STEP
}

interface Props {
  currentPrice?: number
}

export default function RiskCalculator({ currentPrice }: Props) {
  const { t } = useT()
  const { bot } = useBot()
  const meta = BOT_META[bot]
  const cfg = RISK_CONFIG[bot]

  const defaultRiskPct = cfg.riskPerTrade * 100

  const [open, setOpen] = useState(false)
  const [capitalStr, setCapitalStr] = useState('')
  const [leverage, setLeverage] = useState(0)
  const [riskPctStr, setRiskPctStr] = useState(String(defaultRiskPct))

  const capital = parseFloat(capitalStr) || 0
  const riskPct = Math.max(0.01, Math.min(100, parseFloat(riskPctStr) || defaultRiskPct))
  const riskFrac = riskPct / 100
  const isDefaultRisk = Math.abs(riskPct - defaultRiskPct) < 0.001

  const scenarios = useMemo<Scenario[]>(() => {
    if (capital <= 0) return []
    const price = currentPrice ?? (bot === 'gold' ? 2400 : 1.27)

    if (cfg.instrumentType === 'gold') {
      const slLevels = [
        { sl: cfg.slMin, label: t.riskCalcMin, slLabel: `$${cfg.slMin} SL` },
        { sl: cfg.slMid, label: t.riskCalcTypical, slLabel: `$${cfg.slMid} SL` },
        { sl: cfg.slMax, label: t.riskCalcMax, slLabel: `$${cfg.slMax} SL` },
      ]
      return slLevels.map(({ sl, label, slLabel }) => {
        const lot = floorLot((capital * riskFrac) / (sl * cfg.contractSize))
        const feasible = lot >= MIN_LOT
        const riskUsd = feasible ? lot * sl * cfg.contractSize : 0
        const marginUsd = leverage > 0 && feasible
          ? (lot * price * cfg.contractSize) / leverage
          : null
        return { label, slLabel, lot, riskUsd, marginUsd, feasible }
      })
    } else {
      // Forex
      const forexCfg = cfg as typeof RISK_CONFIG.forex
      const slLevels = [
        { sl: forexCfg.slMin, label: t.riskCalcMin, slLabel: `${forexCfg.slMin} pip` },
        { sl: forexCfg.slMid, label: t.riskCalcTypical, slLabel: `${forexCfg.slMid} pip` },
        { sl: forexCfg.slMax, label: t.riskCalcMax, slLabel: `${forexCfg.slMax} pip` },
      ]
      return slLevels.map(({ sl, label, slLabel }) => {
        const lot = floorLot((capital * riskFrac) / (sl * forexCfg.pipValuePerLot))
        const feasible = lot >= MIN_LOT
        const riskUsd = feasible ? lot * sl * forexCfg.pipValuePerLot : 0
        const marginUsd = leverage > 0 && feasible
          ? (lot * forexCfg.contractSize * price) / leverage
          : null
        return { label, slLabel, lot, riskUsd, marginUsd, feasible }
      })
    }
  }, [capital, riskFrac, leverage, bot, cfg, currentPrice, t])

  // Minimum capital required for 0.01 lot at the smallest SL
  const minCapital = useMemo(() => {
    if (cfg.instrumentType === 'gold') {
      return (MIN_LOT * cfg.slMin * cfg.contractSize) / riskFrac
    }
    const forexCfg = cfg as typeof RISK_CONFIG.forex
    return (MIN_LOT * forexCfg.slMin * forexCfg.pipValuePerLot) / riskFrac
  }, [cfg, riskFrac])

  const allFeasible = scenarios.length > 0 && scenarios.every(s => s.feasible)
  const someFeasible = scenarios.some(s => s.feasible)
  const verdict: 'ok' | 'warn' | 'fail' | null =
    capital <= 0 ? null : allFeasible ? 'ok' : someFeasible ? 'warn' : 'fail'

  const maxLossStreak = Math.floor(0.5 / riskFrac)

  const VERDICT = {
    ok: {
      color: 'text-lime-400',
      bg: 'bg-lime-500/10 border-lime-500/30',
      icon: '✓',
      title: t.riskCalcOkTitle,
    },
    warn: {
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/30',
      icon: '⚠',
      title: t.riskCalcWarnTitle,
    },
    fail: {
      color: 'text-red-400',
      bg: 'bg-red-500/10 border-red-500/30',
      icon: '✕',
      title: t.riskCalcFailTitle(minCapital.toLocaleString(undefined, { maximumFractionDigits: 0 })),
    },
  }

  return (
    <>
      {/* Trigger */}
      <button
        onClick={() => setOpen(true)}
        className={`
          text-[9px] font-mono font-semibold uppercase tracking-[0.15em]
          px-2.5 py-1 rounded border
          ${meta.accentBorder} ${meta.accentBg} ${meta.accent}
          hover:opacity-75 transition-opacity cursor-pointer
        `}
      >
        {t.riskCalcBtn}
      </button>

      {/* Backdrop + Modal */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          onClick={e => { if (e.target === e.currentTarget) setOpen(false) }}
        >
          <div className="w-full max-w-sm bg-zinc-900 border border-zinc-700/60 rounded-2xl shadow-2xl overflow-hidden">

            {/* Header */}
            <div className={`flex items-center justify-between px-5 py-4 border-b border-zinc-800/80 ${meta.accentBg}`}>
              <div>
                <p className={`${meta.accent} text-[10px] font-mono font-bold uppercase tracking-[0.2em]`}>
                  {t.riskCalcTitle}
                </p>
                <p className="text-zinc-500 text-[11px] font-mono mt-0.5">
                  {t.riskCalcSubtitle(riskPct.toFixed(riskPct < 1 ? 2 : 1), meta.symbol)}
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-zinc-600 hover:text-zinc-300 transition-colors w-6 h-6 flex items-center justify-center text-sm"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-4">

              {/* Inputs */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-zinc-500 text-[9px] font-mono uppercase tracking-[0.15em] block mb-1.5">
                    {t.riskCalcCapital}
                  </label>
                  <input
                    type="number"
                    min={0}
                    placeholder="e.g. 5000"
                    value={capitalStr}
                    onChange={e => setCapitalStr(e.target.value)}
                    className="w-full bg-zinc-800/80 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 font-mono text-sm focus:outline-none focus:border-zinc-500 tabular-nums placeholder-zinc-700"
                  />
                </div>
                <div>
                  <label className="text-zinc-500 text-[9px] font-mono uppercase tracking-[0.15em] block mb-1.5">
                    {t.riskCalcLeverage} <span className="text-zinc-700 normal-case">{t.riskCalcLeverageOptional}</span>
                  </label>
                  <select
                    value={leverage}
                    onChange={e => setLeverage(Number(e.target.value))}
                    className="w-full bg-zinc-800/80 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 font-mono text-sm focus:outline-none focus:border-zinc-500"
                  >
                    {LEVERAGE_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Risk % input */}
              <div>
                <label className="text-zinc-500 text-[9px] font-mono uppercase tracking-[0.15em] block mb-1.5">
                  {t.riskCalcRiskPct}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min={0.01}
                    max={100}
                    step={0.1}
                    value={riskPctStr}
                    onChange={e => setRiskPctStr(e.target.value)}
                    className="w-full bg-zinc-800/80 border border-zinc-700 rounded-lg px-3 py-2 pr-24 text-zinc-100 font-mono text-sm focus:outline-none focus:border-zinc-500 tabular-nums"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[10px] pointer-events-none flex items-center gap-1.5">
                    <span className="text-zinc-500">%</span>
                    {isDefaultRisk && (
                      <span className={`${meta.accent} opacity-70`}>— {t.riskCalcDefault}</span>
                    )}
                  </span>
                </div>
              </div>

              {/* Scenarios Table */}
              {capital > 0 ? (
                <div className="rounded-xl border border-zinc-800 overflow-hidden">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="bg-zinc-800/50">
                        <th className="text-left text-zinc-600 uppercase tracking-widest px-3 py-2 text-[9px] font-medium">
                          {t.riskCalcScenario}
                        </th>
                        <th className="text-right text-zinc-600 uppercase tracking-widest px-3 py-2 text-[9px] font-medium">
                          {t.riskCalcLot}
                        </th>
                        <th className="text-right text-zinc-600 uppercase tracking-widest px-3 py-2 text-[9px] font-medium">
                          {t.riskCalcRisk}
                        </th>
                        {leverage > 0 && (
                          <th className="text-right text-zinc-600 uppercase tracking-widest px-3 py-2 text-[9px] font-medium">
                            {t.riskCalcMargin}
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/80">
                      {scenarios.map((s, i) => (
                        <tr key={i} className={!s.feasible ? 'opacity-35' : ''}>
                          <td className="px-3 py-2.5">
                            <span className="text-zinc-300">{s.label}</span>
                            <span className="text-zinc-600 ml-1.5 text-[10px]">{s.slLabel}</span>
                          </td>
                          <td className="px-3 py-2.5 text-right tabular-nums">
                            {s.feasible
                              ? <span className={meta.accent}>{s.lot.toFixed(2)}</span>
                              : <span className="text-red-500/70">—</span>
                            }
                          </td>
                          <td className="px-3 py-2.5 text-right tabular-nums">
                            {s.feasible
                              ? <span className="text-zinc-200">${s.riskUsd.toFixed(0)}</span>
                              : <span className="text-red-500/70">—</span>
                            }
                          </td>
                          {leverage > 0 && (
                            <td className="px-3 py-2.5 text-right tabular-nums">
                              {s.marginUsd != null
                                ? <span className="text-zinc-400">${s.marginUsd.toFixed(0)}</span>
                                : <span className="text-red-500/70">—</span>
                              }
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="rounded-xl border border-zinc-800/50 px-4 py-6 text-center">
                  <p className="text-zinc-600 text-[11px] font-mono">
                    {t.riskCalcEmpty}
                  </p>
                </div>
              )}

              {/* Verdict */}
              {verdict && (
                <div className={`rounded-xl border px-4 py-3 ${VERDICT[verdict].bg}`}>
                  <p className={`${VERDICT[verdict].color} text-sm font-mono font-semibold flex items-center gap-2`}>
                    <span className="w-4 text-center">{VERDICT[verdict].icon}</span>
                    {VERDICT[verdict].title}
                  </p>
                  {verdict !== 'fail' ? (
                    <p className="text-zinc-500 text-[11px] font-mono mt-1 ml-6">
                      {t.riskCalcDrawdown(maxLossStreak)}
                    </p>
                  ) : (
                    <p className="text-zinc-500 text-[11px] font-mono mt-1 ml-6">
                      {t.riskCalcMinLot}
                    </p>
                  )}
                </div>
              )}

              {/* High leverage warning */}
              {leverage >= HIGH_LEVERAGE_THRESHOLD && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/8 px-4 py-2.5 flex items-start gap-2">
                  <span className="text-red-400 text-sm leading-none mt-0.5">⚠</span>
                  <div>
                    <p className="text-red-400 text-[11px] font-mono font-semibold">{t.riskCalcHighLevWarn(leverage)}</p>
                    <p className="text-zinc-500 text-[10px] font-mono mt-0.5 leading-relaxed">
                      {t.riskCalcHighLevDesc(((1 / leverage) * 100).toFixed(2))}
                    </p>
                  </div>
                </div>
              )}

              {/* Footer note */}
              <p className="text-zinc-700 text-[10px] font-mono text-center leading-relaxed">
                {leverage > 0
                  ? t.riskCalcFooter(
                      currentPrice?.toFixed(bot === 'gold' ? 2 : 5) ?? (bot === 'gold' ? '2400.00' : '1.27000'),
                      ` at 1:${leverage}`
                    )
                  : t.riskCalcFooterNoLev(
                      currentPrice?.toFixed(bot === 'gold' ? 2 : 5) ?? (bot === 'gold' ? '2400.00' : '1.27000')
                    )
                }
              </p>

            </div>
          </div>
        </div>
      )}
    </>
  )
}
