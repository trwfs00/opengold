# Phase 5 Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js 14 web dashboard that polls the FastAPI backend every 5 seconds and displays 7 panels: live candle chart, signals breakdown, account info, decisions journal, trades log, P&L stats, and kill switch.

**Architecture:** Single-page app in `dashboard/` using App Router. All data fetched from `http://localhost:8000/api/*`. Tailwind CSS for layout. Lightweight Charts (TradingView) for candlestick and line charts. Auto-polling via `setInterval` every 5 seconds.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS 3, `lightweight-charts` ^4, `clsx` (optional for conditional classes)

**Requires:** Phase 5 backend running locally (`uvicorn src.api.app:app --host 127.0.0.1 --port 8000`)

**Spec:** `docs/superpowers/specs/2026-03-25-phase5-preflight-dashboard.md`

**No automated tests** — verification is manual browser inspection.

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `dashboard/package.json` | Next.js 14 + TypeScript + Tailwind deps |
| Create | `dashboard/tsconfig.json` | TypeScript config |
| Create | `dashboard/tailwind.config.ts` | Tailwind config |
| Create | `dashboard/postcss.config.js` | PostCSS for Tailwind |
| Create | `dashboard/next.config.js` | Next.js config (API proxy) |
| Create | `dashboard/app/layout.tsx` | Root layout with Tailwind globals |
| Create | `dashboard/app/globals.css` | Tailwind base styles |
| Create | `dashboard/lib/api.ts` | Typed fetch helpers for all 8 endpoints |
| Create | `dashboard/components/StatusBar.tsx` | Top bar: bot alive / kill switch |
| Create | `dashboard/components/AccountPanel.tsx` | Balance, equity, open positions |
| Create | `dashboard/components/CandleChart.tsx` | Lightweight Charts candlestick |
| Create | `dashboard/components/SignalsPanel.tsx` | Per-strategy signal cards |
| Create | `dashboard/components/DecisionsTable.tsx` | Last 50 decisions rows |
| Create | `dashboard/components/TradesTable.tsx` | Last 50 closed trades rows |
| Create | `dashboard/components/StatsPanel.tsx` | Win rate + P&L curve line chart |
| Create | `dashboard/app/page.tsx` | Root page — imports all components + polling |

---

## Task 1: Scaffold Next.js app

- [ ] **Step 1: Create `dashboard/package.json`**

```json
{
  "name": "opengold-dashboard",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000"
  },
  "dependencies": {
    "next": "14.2.4",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "lightweight-charts": "^4.2.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.4",
    "postcss": "^8.4",
    "tailwindcss": "^3.4",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: Create `dashboard/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `dashboard/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss'
const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: { extend: {} },
  plugins: [],
}
export default config
```

- [ ] **Step 4: Create `dashboard/postcss.config.js`**

```javascript
module.exports = {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
```

- [ ] **Step 5: Create `dashboard/next.config.js`**

This proxies `/api/*` to the FastAPI backend to avoid CORS issues in dev:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ]
  },
}
module.exports = nextConfig
```

- [ ] **Step 6: Create `dashboard/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 7: Create `dashboard/app/layout.tsx`**

```typescript
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'OpenGold Dashboard',
  description: 'Live trading monitor',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 8: Create minimal `dashboard/app/page.tsx` (placeholder)**

```typescript
export default function Page() {
  return <div className="p-4 text-xl">OpenGold Dashboard loading...</div>
}
```

- [ ] **Step 9: Install dependencies and verify dev server starts**

```powershell
cd D:\hobbies\opengold\dashboard
npm install
npm run dev
```

Expected: `ready - started server on 0.0.0.0:3000` and `http://localhost:3000` shows the placeholder.

- [ ] **Step 10: Commit**

```powershell
cd D:\hobbies\opengold
git add dashboard/
git commit -m "feat: scaffold Next.js 14 dashboard with Tailwind"
```

---

## Task 2: API fetch helpers

**File:** `dashboard/lib/api.ts`

- [ ] **Step 1: Create `dashboard/lib/api.ts`**

```typescript
const BASE = '/api'

export interface CandleBar {
  time: number   // Unix epoch seconds
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface AccountInfo {
  balance: number | null
  equity: number | null
  currency: string | null
  positions: PositionInfo[]
  error?: string
}

export interface PositionInfo {
  ticket: number
  symbol: string
  direction: string
  lots: number
  open_price: number
  current_price: number
  unrealized_pnl: number
}

export interface SignalsData {
  regime: string | null
  buy_score: number | null
  sell_score: number | null
  connected: boolean
  signals: Record<string, { signal: string; confidence: number }> | null
  message?: string
  error?: string
}

export interface DecisionRow {
  time: string
  regime: string
  buy_score: number
  sell_score: number
  trigger_fired: boolean
  ai_action: string | null
  ai_confidence: number | null
  ai_sl: number | null
  ai_tp: number | null
  risk_block_reason: string | null
}

export interface TradeRow {
  open_time: string
  close_time: string
  direction: string
  lot_size: number
  open_price: number
  close_price: number
  sl: number
  tp: number
  pnl: number
  result: string
}

export interface PnlPoint {
  time: number    // Unix epoch seconds
  value: number   // cumulative P&L
}

export interface StatsData {
  win_rate: number | null
  total_pnl: number
  avg_win: number | null
  avg_loss: number | null
  pnl_curve: PnlPoint[]
}

export interface StatusData {
  bot_alive: boolean
  dry_run: boolean
  kill_switch_active: boolean
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export const fetchCandles = (limit = 200) =>
  get<{ data: CandleBar[] }>(`/candles?limit=${limit}`).then(r => r.data ?? [])

export const fetchAccount = () => get<AccountInfo>('/account')

export const fetchSignals = () => get<SignalsData>('/signals')

export const fetchDecisions = (limit = 50) =>
  get<{ data: DecisionRow[] }>(`/decisions?limit=${limit}`).then(r => r.data ?? [])

export const fetchTrades = (limit = 50) =>
  get<{ data: TradeRow[] }>(`/trades?limit=${limit}`).then(r => r.data ?? [])

export const fetchStats = () => get<StatsData>('/stats')

export const fetchStatus = () => get<StatusData>('/status')

export async function postKillSwitch(active: boolean): Promise<{ active: boolean }> {
  const res = await fetch(`${BASE}/killswitch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active }),
  })
  if (!res.ok) throw new Error(`killswitch: HTTP ${res.status}`)
  return res.json()
}
```

- [ ] **Step 2: Commit**

```powershell
git add dashboard/lib/api.ts
git commit -m "feat: typed API fetch helpers for all 8 endpoints"
```

---

## Task 3: StatusBar + AccountPanel

**Files:**
- Create: `dashboard/components/StatusBar.tsx`
- Create: `dashboard/components/AccountPanel.tsx`

- [ ] **Step 1: Create `dashboard/components/StatusBar.tsx`**

```typescript
'use client'
import { StatusData } from '@/lib/api'

interface Props {
  status: StatusData | null
  onKillSwitch: (active: boolean) => void
}

export default function StatusBar({ status, onKillSwitch }: Props) {
  if (!status) return <div className="h-10 bg-gray-900 animate-pulse" />

  const alive = status.bot_alive
  const ksActive = status.kill_switch_active

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800 text-sm">
      <div className="flex items-center gap-4">
        <span className={`font-semibold ${alive ? 'text-green-400' : 'text-red-400'}`}>
          {alive ? '● BOT ALIVE' : '● BOT OFFLINE'}
        </span>
        {status.dry_run && (
          <span className="text-yellow-400 font-medium">DRY RUN</span>
        )}
      </div>
      <button
        onClick={() => onKillSwitch(!ksActive)}
        className={`px-3 py-1 rounded font-semibold transition-colors ${
          ksActive
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : 'bg-gray-700 hover:bg-gray-600 text-gray-200'
        }`}
      >
        {ksActive ? 'KILL SWITCH ON — Click to Resume' : 'Kill Switch'}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Create `dashboard/components/AccountPanel.tsx`**

```typescript
'use client'
import { AccountInfo } from '@/lib/api'

interface Props {
  account: AccountInfo | null
}

export default function AccountPanel({ account }: Props) {
  return (
    <div className="rounded-lg bg-gray-900 p-4 border border-gray-800">
      <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">Account</h2>
      {!account || account.error ? (
        <p className="text-gray-500 text-sm">{account?.error ?? 'Loading...'}</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <Stat label="Balance" value={account.balance?.toFixed(2)} unit={account.currency ?? ''} />
            <Stat label="Equity" value={account.equity?.toFixed(2)} unit={account.currency ?? ''} />
            <Stat label="Positions" value={String(account.positions?.length ?? 0)} unit="" />
          </div>
          {account.positions && account.positions.length > 0 && (
            <table className="w-full text-xs text-gray-300">
              <thead>
                <tr className="text-gray-500 text-left">
                  <th className="pb-1">Symbol</th>
                  <th>Dir</th>
                  <th>Lots</th>
                  <th>P&L</th>
                </tr>
              </thead>
              <tbody>
                {account.positions.map(p => (
                  <tr key={p.ticket} className="border-t border-gray-800">
                    <td className="py-1">{p.symbol}</td>
                    <td>{p.direction}</td>
                    <td>{p.lots}</td>
                    <td className={p.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {p.unrealized_pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}

function Stat({ label, value, unit }: { label: string; value?: string; unit: string }) {
  return (
    <div>
      <p className="text-gray-500 text-xs">{label}</p>
      <p className="text-white font-semibold">{value ?? '—'} <span className="text-gray-400 text-xs">{unit}</span></p>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```powershell
git add dashboard/components/StatusBar.tsx dashboard/components/AccountPanel.tsx
git commit -m "feat: StatusBar and AccountPanel components"
```

---

## Task 4: CandleChart

**File:** `dashboard/components/CandleChart.tsx`

Lightweight Charts replaces the DOM canvas — must use `useRef` + `useEffect` and only run after mount (no SSR).

- [ ] **Step 1: Create `dashboard/components/CandleChart.tsx`**

```typescript
'use client'
import { useEffect, useRef } from 'react'
import { CandleBar } from '@/lib/api'

interface Props {
  candles: CandleBar[]
}

export default function CandleChart({ candles }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof import('lightweight-charts')['createChart']> | null>(null)
  const seriesRef = useRef<ReturnType<ReturnType<typeof import('lightweight-charts')['createChart']>['addCandlestickSeries']> | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (chartRef.current) {
        chartRef.current.remove()
      }
      const chart = createChart(containerRef.current!, {
        layout: {
          background: { type: ColorType.Solid, color: '#111827' },
          textColor: '#9ca3af',
        },
        grid: {
          vertLines: { color: '#1f2937' },
          horzLines: { color: '#1f2937' },
        },
        width: containerRef.current!.clientWidth,
        height: 300,
        timeScale: { timeVisible: true, secondsVisible: false },
      })
      const series = chart.addCandlestickSeries({
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
      })
      chartRef.current = chart
      seriesRef.current = series
      if (candles.length) {
        series.setData(candles)
        chart.timeScale().fitContent()
      }
    })
    return () => {
      chartRef.current?.remove()
      chartRef.current = null
    }
  }, [])  // mount only

  // Update data without recreating chart
  useEffect(() => {
    if (seriesRef.current && candles.length) {
      seriesRef.current.setData(candles)
      chartRef.current?.timeScale().fitContent()
    }
  }, [candles])

  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4">
      <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">XAUUSD — 1H</h2>
      <div ref={containerRef} />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```powershell
git add dashboard/components/CandleChart.tsx
git commit -m "feat: CandleChart using Lightweight Charts"
```

---

## Task 5: SignalsPanel

**File:** `dashboard/components/SignalsPanel.tsx`

- [ ] **Step 1: Create `dashboard/components/SignalsPanel.tsx`**

```typescript
'use client'
import { SignalsData } from '@/lib/api'

interface Props {
  signals: SignalsData | null
}

export default function SignalsPanel({ signals }: Props) {
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4">
      <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">Signals</h2>
      {!signals ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : signals.error ? (
        <p className="text-red-400 text-sm">{signals.error}</p>
      ) : (
        <>
          <div className="flex items-center gap-4 mb-4">
            <Badge label="Regime" value={signals.regime ?? '—'} />
            <Badge label="Buy" value={signals.buy_score?.toFixed(2) ?? '—'} color="text-green-400" />
            <Badge label="Sell" value={signals.sell_score?.toFixed(2) ?? '—'} color="text-red-400" />
            {!signals.connected && (
              <span className="text-yellow-400 text-xs">MT5 disconnected</span>
            )}
          </div>
          {signals.message && (
            <p className="text-gray-500 text-sm">{signals.message}</p>
          )}
          {signals.signals && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(signals.signals).map(([name, data]) => (
                <div key={name} className="bg-gray-800 rounded p-2 text-xs">
                  <p className="text-gray-400 mb-1">{name}</p>
                  <span className={data.signal === 'BUY' ? 'text-green-400' : data.signal === 'SELL' ? 'text-red-400' : 'text-gray-300'}>
                    {data.signal}
                  </span>
                  <span className="text-gray-500 ml-2">{(data.confidence * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Badge({ label, value, color = 'text-white' }: { label: string; value: string; color?: string }) {
  return (
    <div className="text-center">
      <p className="text-gray-500 text-xs">{label}</p>
      <p className={`font-semibold ${color}`}>{value}</p>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```powershell
git add dashboard/components/SignalsPanel.tsx
git commit -m "feat: SignalsPanel component"
```

---

## Task 6: DecisionsTable + TradesTable

**Files:**
- Create: `dashboard/components/DecisionsTable.tsx`
- Create: `dashboard/components/TradesTable.tsx`

- [ ] **Step 1: Create `dashboard/components/DecisionsTable.tsx`**

```typescript
'use client'
import { DecisionRow } from '@/lib/api'

interface Props {
  decisions: DecisionRow[]
}

export default function DecisionsTable({ decisions }: Props) {
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4">
      <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">
        Decisions Journal ({decisions.length})
      </h2>
      {decisions.length === 0 ? (
        <p className="text-gray-500 text-sm">No decisions yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-gray-300">
            <thead>
              <tr className="text-gray-500 text-left border-b border-gray-800">
                <th className="pb-2 pr-3">Time</th>
                <th className="pr-3">Regime</th>
                <th className="pr-3">Buy</th>
                <th className="pr-3">Sell</th>
                <th className="pr-3">AI Action</th>
                <th className="pr-3">Conf</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((row, i) => (
                <tr key={i} className="border-t border-gray-800 hover:bg-gray-800">
                  <td className="py-1 pr-3 text-gray-500">{new Date(row.time).toLocaleTimeString()}</td>
                  <td className="pr-3">{row.regime ?? '—'}</td>
                  <td className="pr-3 text-green-400">{row.buy_score?.toFixed(1)}</td>
                  <td className="pr-3 text-red-400">{row.sell_score?.toFixed(1)}</td>
                  <td className={`pr-3 font-medium ${row.ai_action === 'BUY' ? 'text-green-400' : row.ai_action === 'SELL' ? 'text-red-400' : ''}`}>
                    {row.ai_action ?? '—'}
                  </td>
                  <td className="pr-3">{row.ai_confidence ? `${(row.ai_confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td className="text-gray-500">{row.risk_block_reason ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create `dashboard/components/TradesTable.tsx`**

```typescript
'use client'
import { TradeRow } from '@/lib/api'

interface Props {
  trades: TradeRow[]
}

export default function TradesTable({ trades }: Props) {
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4">
      <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">
        Trades ({trades.length})
      </h2>
      {trades.length === 0 ? (
        <p className="text-gray-500 text-sm">No closed trades yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-gray-300">
            <thead>
              <tr className="text-gray-500 text-left border-b border-gray-800">
                <th className="pb-2 pr-3">Closed</th>
                <th className="pr-3">Dir</th>
                <th className="pr-3">Lots</th>
                <th className="pr-3">Open</th>
                <th className="pr-3">Close</th>
                <th className="pr-3">P&L</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((row, i) => (
                <tr key={i} className="border-t border-gray-800 hover:bg-gray-800">
                  <td className="py-1 pr-3 text-gray-500">{new Date(row.close_time).toLocaleTimeString()}</td>
                  <td className={`pr-3 font-medium ${row.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                    {row.direction}
                  </td>
                  <td className="pr-3">{row.lot_size}</td>
                  <td className="pr-3">{row.open_price.toFixed(2)}</td>
                  <td className="pr-3">{row.close_price.toFixed(2)}</td>
                  <td className={`pr-3 font-semibold ${row.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {row.pnl >= 0 ? '+' : ''}{row.pnl.toFixed(2)}
                  </td>
                  <td className={row.result === 'WIN' ? 'text-green-400' : 'text-red-400'}>{row.result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```powershell
git add dashboard/components/DecisionsTable.tsx dashboard/components/TradesTable.tsx
git commit -m "feat: DecisionsTable and TradesTable components"
```

---

## Task 7: StatsPanel

**File:** `dashboard/components/StatsPanel.tsx`

The P&L curve uses Lightweight Charts line series. Same `useRef`/`useEffect` pattern as CandleChart.

- [ ] **Step 1: Create `dashboard/components/StatsPanel.tsx`**

```typescript
'use client'
import { useEffect, useRef } from 'react'
import { StatsData } from '@/lib/api'

interface Props {
  stats: StatsData | null
}

export default function StatsPanel({ stats }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof import('lightweight-charts')['createChart']> | null>(null)
  const seriesRef = useRef<ReturnType<ReturnType<typeof import('lightweight-charts')['createChart']>['addLineSeries']> | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (chartRef.current) chartRef.current.remove()
      const chart = createChart(containerRef.current!, {
        layout: {
          background: { type: ColorType.Solid, color: '#111827' },
          textColor: '#9ca3af',
        },
        grid: {
          vertLines: { color: '#1f2937' },
          horzLines: { color: '#1f2937' },
        },
        width: containerRef.current!.clientWidth,
        height: 160,
        timeScale: { timeVisible: true, secondsVisible: false },
      })
      const series = chart.addLineSeries({ color: '#22c55e', lineWidth: 2 })
      chartRef.current = chart
      seriesRef.current = series
      if (stats?.pnl_curve?.length) {
        series.setData(stats.pnl_curve)
        chart.timeScale().fitContent()
      }
    })
    return () => { chartRef.current?.remove(); chartRef.current = null }
  }, [])

  useEffect(() => {
    if (seriesRef.current && stats?.pnl_curve?.length) {
      seriesRef.current.setData(stats.pnl_curve)
      chartRef.current?.timeScale().fitContent()
    }
  }, [stats?.pnl_curve])

  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 p-4">
      <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">Statistics</h2>
      {!stats ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-3 mb-4">
            <Stat label="Win Rate" value={stats.win_rate !== null ? `${(stats.win_rate * 100).toFixed(1)}%` : '—'} />
            <Stat label="Total P&L" value={stats.total_pnl !== null ? stats.total_pnl.toFixed(2) : '—'}
              color={stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'} />
            <Stat label="Avg Win" value={stats.avg_win !== null ? `+${stats.avg_win.toFixed(2)}` : '—'} color="text-green-400" />
            <Stat label="Avg Loss" value={stats.avg_loss !== null ? stats.avg_loss.toFixed(2) : '—'} color="text-red-400" />
          </div>
          {stats.pnl_curve.length === 0 ? (
            <p className="text-gray-500 text-sm">No trades yet.</p>
          ) : (
            <div ref={containerRef} />
          )}
        </>
      )}
    </div>
  )
}

function Stat({ label, value, color = 'text-white' }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <p className="text-gray-500 text-xs">{label}</p>
      <p className={`font-semibold ${color}`}>{value}</p>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```powershell
git add dashboard/components/StatsPanel.tsx
git commit -m "feat: StatsPanel with P&L curve line chart"
```

---

## Task 8: Wire page.tsx with polling

**File:** `dashboard/app/page.tsx`

- [ ] **Step 1: Create `dashboard/app/page.tsx`**

```typescript
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

const POLL_INTERVAL_MS = 5000

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
    const id = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const handleKillSwitch = async (active: boolean) => {
    try {
      await postKillSwitch(active)
      await fetchStatus().then(setStatus)
    } catch (e) {
      console.error('Kill switch failed:', e)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <StatusBar status={status} onKillSwitch={handleKillSwitch} />
      <main className="p-4 grid gap-4">
        {/* Row 1: Chart */}
        <CandleChart candles={candles} />

        {/* Row 2: Signals + Account */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SignalsPanel signals={signals} />
          <AccountPanel account={account} />
        </div>

        {/* Row 3: Stats */}
        <StatsPanel stats={stats} />

        {/* Row 4: Tables */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <DecisionsTable decisions={decisions} />
          <TradesTable trades={trades} />
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Start backend and dashboard, verify in browser**

```powershell
# Terminal 1: start FastAPI backend
uvicorn src.api.app:app --host 127.0.0.1 --port 8000

# Terminal 2: start Next.js dev server
cd dashboard
npm run dev
```

Open `http://localhost:3000` in browser. Verify:
- [ ] StatusBar shows bot status + kill switch button
- [ ] CandleChart renders (or shows empty if no candles)
- [ ] SignalsPanel shows regime/scores (or "No data yet")
- [ ] AccountPanel shows balance and equity
- [ ] StatsPanel shows stats panels
- [ ] Tables load (or show "No X yet" empty states)
- [ ] Data refreshes every 5 seconds (watch network tab)
- [ ] Kill switch button toggles and re-fetches status

- [ ] **Step 3: Final commit + tag**

```powershell
cd D:\hobbies\opengold
git add dashboard/app/page.tsx
git commit -m "feat: wire page.tsx with 5s polling — Phase 5 dashboard complete"
git tag v0.4.0-dashboard
```
