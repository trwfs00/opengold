# Multi-Symbol Forex Scalper — Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Next.js dashboard to display either the Gold bot or Forex Scalper via pill tabs, routing API calls to port 8000 (Gold) or port 8001 (Forex) based on the selected bot.

**Architecture:** React context (`BotContext`) holds the active bot selection. All API calls route through `/api/{bot}/` prefixed rewrites in `next.config.js`. `BotTabSwitcher` renders in `StatusBar`. `page.tsx` reads `bot` from context and passes it to every fetch call.

**Tech Stack:** Next.js 14, TypeScript, React context, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-03-26-multi-symbol-forex-scalper-design.md`

**Prerequisite:** Backend plan `docs/superpowers/plans/2026-03-26-forex-backend.md` should be complete (or at minimum Task 5 so API endpoints exist on port 8001).

**Dev server:** `cd dashboard && npm run dev`

---

## File Map

| File | Change |
|---|---|
| `dashboard/next.config.js` | Two rewrite rules: `/api/gold/*` and `/api/forex/*` |
| `dashboard/context/BotContext.tsx` | **New directory + file** — `BotContext`, `BotProvider`, `useBot()` hook |
| `dashboard/lib/api.ts` | All exported functions gain `bot: 'gold' \| 'forex'` parameter |
| `dashboard/components/BotTabSwitcher.tsx` | New — pill tab UI ("GOLD" / "FOREX") |
| `dashboard/components/StatusBar.tsx` | Import and render `BotTabSwitcher` |
| `dashboard/app/layout.tsx` | Wrap with `BotProvider` |
| `dashboard/app/page.tsx` | Read `bot` from `useBot()`, pass to all API calls; fix `handleKillSwitch` |
| `dashboard/components/CandleChart.tsx` | Add `useBot()` + pass `bot` to `fetchCandles` |
| `dashboard/components/ClaudeThought.tsx` | Add `useBot()` + pass `bot` to `fetchDecisions` |
| `dashboard/components/DecisionsTable.tsx` | Add `useBot()` + pass `bot` to `fetchDecisions` |
| `dashboard/components/AnalyticsPanel.tsx` | Add `useBot()` + pass `bot` to `fetchRegimeStats` |

---

## Task 1: Update `dashboard/next.config.js` — dual API rewrites

**Files:**
- Modify: `dashboard/next.config.js`

- [ ] **Step 1: Replace the single rewrite with two bot-prefixed rewrites**

Replace the entire `next.config.js` content with:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/gold/:path*',
        destination: `${process.env.GOLD_API_URL || 'http://127.0.0.1:8000'}/api/:path*`,
      },
      {
        source: '/api/forex/:path*',
        destination: `${process.env.FOREX_API_URL || 'http://127.0.0.1:8001'}/api/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
```

Note: `GOLD_API_URL` and `FOREX_API_URL` are optional. Set them in `dashboard/.env.local` for non-localhost deployments:
```ini
GOLD_API_URL=http://127.0.0.1:8000
FOREX_API_URL=http://127.0.0.1:8001
```

- [ ] **Step 2: Restart the dev server and verify routing**

```bash
# In dashboard/
npm run dev
```

Then verify (Gold backend must be running on port 8000):

```bash
curl http://localhost:3000/api/gold/status
# Expected: JSON status response from Gold bot

curl http://localhost:3000/api/forex/status
# Expected: either JSON from Forex bot (if running) or connection error (not 404)
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/next.config.js
git commit -m "feat(dashboard): dual API rewrites /api/gold/* and /api/forex/*"
```

---

## Task 2: Create `dashboard/context/BotContext.tsx`

**Files:**
- Create: `dashboard/context/BotContext.tsx`

- [ ] **Step 1: Create the `dashboard/context/` directory and the context file**

The `dashboard/context/` directory is new — create it:

```bash
mkdir dashboard/context
```

```tsx
'use client'
import { createContext, useContext, useState, ReactNode } from 'react'

export type BotId = 'gold' | 'forex'

interface BotContextValue {
  bot: BotId
  setBot: (bot: BotId) => void
}

const BotContext = createContext<BotContextValue>({
  bot: 'gold',
  setBot: () => {},
})

export function BotProvider({ children }: { children: ReactNode }) {
  const [bot, setBot] = useState<BotId>('gold')
  return (
    <BotContext.Provider value={{ bot, setBot }}>
      {children}
    </BotContext.Provider>
  )
}

export function useBot(): BotContextValue {
  return useContext(BotContext)
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd dashboard && npx tsc --noEmit
```

Expected: no errors for the new file.

- [ ] **Step 3: Commit**

```bash
git add dashboard/context/BotContext.tsx
git commit -m "feat(dashboard): add BotContext + BotProvider + useBot() hook"
```

---

## Task 3: Update `dashboard/lib/api.ts` — add `bot` parameter to all functions

**Files:**
- Modify: `dashboard/lib/api.ts`

- [ ] **Step 1: Replace `const BASE = '/api'` with a bot-aware helper**

Replace the first line:

```ts
const BASE = '/api'
```

with:

```ts
const BASE = (bot: 'gold' | 'forex') => `/api/${bot}`
```

- [ ] **Step 2: Add `bot` parameter to the `get` helper and all exported functions**

Replace the internal `get` helper:

```ts
async function get<T>(path: string, bot: 'gold' | 'forex'): Promise<T> {
  const res = await fetch(`${BASE(bot)}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`)
  return res.json() as Promise<T>
}
```

Then update every exported function to accept and forward `bot`. Replace the full block of exported functions (from `fetchCandles` through `postKillSwitch`) with:

```ts
export const fetchCandles = (bot: 'gold' | 'forex', limit = 200) =>
  get<{ data: CandleBar[] }>(`/candles?limit=${limit}`, bot).then(r => r.data ?? [])

export const fetchAccount = (bot: 'gold' | 'forex') =>
  get<AccountInfo>('/account', bot)

export const fetchSignals = (bot: 'gold' | 'forex') =>
  get<SignalsData>('/signals', bot)

export const fetchDecisions = (bot: 'gold' | 'forex', opts: { limit?: number; date_from?: string; date_to?: string } = {}) => {
  const { limit = 1000, date_from, date_to } = opts
  const params = new URLSearchParams({ limit: String(limit) })
  if (date_from) params.set('date_from', date_from)
  if (date_to) params.set('date_to', date_to)
  return get<{ data: DecisionRow[] }>(`/decisions?${params}`, bot).then(r => r.data ?? [])
}

export const fetchTrades = (bot: 'gold' | 'forex', limit = 50) =>
  get<{ data: TradeRow[] }>(`/trades?limit=${limit}`, bot).then(r => r.data ?? [])

export const fetchStats = (bot: 'gold' | 'forex') =>
  get<StatsData>('/stats', bot)

export const fetchStatus = (bot: 'gold' | 'forex') =>
  get<StatusData>('/status', bot)

export const fetchSummary = (bot: 'gold' | 'forex') =>
  get<SummaryData>('/summary', bot)

export const fetchRegimeStats = (bot: 'gold' | 'forex') =>
  get<RegimeStats>('/regime-stats', bot)

export async function postKillSwitch(bot: 'gold' | 'forex', active: boolean): Promise<{ active: boolean }> {
  const res = await fetch(`${BASE(bot)}/killswitch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active }),
  })
  if (!res.ok) throw new Error(`killswitch: HTTP ${res.status}`)
  return res.json()
}
```

- [ ] **Step 3: Check TypeScript for errors**

```bash
cd dashboard && npx tsc --noEmit
```

Expected: errors about callers in `page.tsx` (they still pass the old signature). These will be fixed in Task 6.

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/api.ts
git commit -m "feat(api): all fetch functions accept bot param for multi-bot routing"
```

---

## Task 4: Create `dashboard/components/BotTabSwitcher.tsx`

**Files:**
- Create: `dashboard/components/BotTabSwitcher.tsx`

- [ ] **Step 1: Create the tab switcher component**

```tsx
'use client'
import { useBot, BotId } from '@/context/BotContext'

const TABS: { id: BotId; label: string }[] = [
  { id: 'gold',  label: 'GOLD' },
  { id: 'forex', label: 'FOREX' },
]

export default function BotTabSwitcher() {
  const { bot, setBot } = useBot()
  return (
    <div className="flex items-center gap-0.5 bg-zinc-800/60 rounded-full p-0.5">
      {TABS.map(tab => (
        <button
          key={tab.id}
          onClick={() => setBot(tab.id)}
          className={`px-3 py-0.5 rounded-full text-[10px] font-semibold tracking-widest transition-all ${
            bot === tab.id
              ? tab.id === 'gold'
                ? 'bg-amber-500 text-zinc-950'
                : 'bg-blue-500 text-zinc-950'
              : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd dashboard && npx tsc --noEmit
```

Expected: only page.tsx errors (being fixed in Task 6), not BotTabSwitcher errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/BotTabSwitcher.tsx
git commit -m "feat(dashboard): BotTabSwitcher pill tabs — GOLD | FOREX"
```

---

## Task 5: Wire `BotProvider` into `dashboard/app/layout.tsx`

**Files:**
- Modify: `dashboard/app/layout.tsx`

- [ ] **Step 1: Import `BotProvider` and wrap children**

Replace the existing `layout.tsx` content with:

```tsx
import type { Metadata } from 'next'
import './globals.css'
import { I18nProvider } from '@/lib/i18n-context'
import { BotProvider } from '@/context/BotContext'

export const metadata: Metadata = {
  title: 'OpenGold Dashboard',
  description: 'Live trading monitor',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <BotProvider>
          <I18nProvider>{children}</I18nProvider>
        </BotProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd dashboard && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/layout.tsx
git commit -m "feat(layout): wrap app in BotProvider for global bot selection state"
```

---

## Task 6: Integrate `BotTabSwitcher` into `StatusBar` and update `page.tsx`

**Files:**
- Modify: `dashboard/components/StatusBar.tsx`
- Modify: `dashboard/app/page.tsx`

- [ ] **Step 1: Add `BotTabSwitcher` to `StatusBar`**

In `StatusBar.tsx`, import the switcher and render it at the start of the status bar:

Add the import after existing imports:

```tsx
import BotTabSwitcher from '@/components/BotTabSwitcher'
```

Inside the returned JSX of `StatusBar`, add `<BotTabSwitcher />` as the first child of the left-side flex group. Find the `<div className="flex items-center gap-5">` and prepend the switcher:

```tsx
      <div className="flex items-center gap-5">
        <BotTabSwitcher />
        <span className={`flex items-center gap-1.5 font-semibold tracking-wide ...`}>
        ...
```

- [ ] **Step 2: Update `page.tsx` to read `bot` from context and pass it to all fetches**

In `page.tsx`, add the import:

```tsx
import { useBot } from '@/context/BotContext'
```

Inside the `Page` component (after the state declarations), add:

```tsx
  const { bot } = useBot()
```

Then update the `refresh` callback to pass `bot` to every API call:

```tsx
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
  }, [bot, refresh])
```

Also update the `handleKillSwitch` function (note: `bot` is already in scope from `useBot()` above):

```tsx
  const handleKillSwitch = async (active: boolean) => {
    try {
      await postKillSwitch(bot, active)
      await fetchStatus(bot).then(setStatus)
    } catch {
      // ignore — status will be refreshed by next poll
    }
  }
```

**Critical:** Without `bot` here, `postKillSwitch` routes to `/api/killswitch` which matches neither `/api/gold/*` nor `/api/forex/*` in the new rewrite rules — the kill switch silently fails.

Note: The dep array must be `[bot]` only — **not** `[bot, refresh]`. Including `refresh` in its own dep array causes `refresh` to be recreated every render → the `useEffect` re-fires on every tick → infinite interval restarts.

```tsx
  }, [bot])
```

Adding `bot` to the dep array means `refresh` reinitialises when the user switches tabs — this intentionally triggers an immediate data reload from the new bot's API.

- [ ] **Step 3: Verify TypeScript has zero errors**

```bash
cd dashboard && npx tsc --noEmit
```

Expected: **zero errors**.

- [ ] **Step 4: Update the four components that call API functions directly**

These four components fetch their own data and must each get `bot` via `useBot()`. The pattern for all four is identical:

**`dashboard/components/CandleChart.tsx`** — calls `fetchCandles(limit)`:  
Add `import { useBot } from '@/context/BotContext'` and `const { bot } = useBot()` inside the component, then change the call to `fetchCandles(bot, limit)`.

**`dashboard/components/ClaudeThought.tsx`** — calls `fetchDecisions({ limit: 1 })`:  
Add `useBot()` and change to `fetchDecisions(bot, { limit: 1 })`.

**`dashboard/components/DecisionsTable.tsx`** — calls `fetchDecisions({...})`:  
Add `useBot()` and pass `bot` as first argument to `fetchDecisions`.

**`dashboard/components/AnalyticsPanel.tsx`** — calls `fetchRegimeStats()`:  
Add `useBot()` and change to `fetchRegimeStats(bot)`.

- [ ] **Step 5: Run TypeScript check after fixing all callers**

```bash
cd dashboard && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 6: Manual smoke test in browser**

Open `http://localhost:3000`. Verify:
- "GOLD" and "FOREX" pill tabs appear in the status bar
- Clicking "GOLD" → data loads from port 8000
- Clicking "FOREX" → either loads Forex data (if bot is running) or shows graceful error state
- Switching back to "GOLD" → Gold data reloads

- [ ] **Step 7: Commit**

```bash
git add dashboard/components/StatusBar.tsx dashboard/app/page.tsx
git commit -m "feat(dashboard): BotTabSwitcher in StatusBar — switches all API calls between Gold and Forex"
```

---

## Task 7: Handle Forex bot offline state

When the Forex bot is not running, `fetchStatus` will throw. The existing `.catch(() => {})` in page.tsx swallows the error and leaves `status` as `null`. In `StatusBar`, `null` status already renders an animated skeleton. This is acceptable minimal behaviour — OFFLINE state is visible.

No code change needed. Verify this works correctly:

- [ ] **Step 1: Verify offline handling**

With only Gold bot running, click the FOREX tab. Confirm:
- Status bar shows skeleton/loading state
- No unhandled errors in browser console
- After a few seconds, status stays null (graceful)

- [ ] **Step 2: Commit (no code — just mark verified)**

```bash
git commit --allow-empty -m "verified: Forex offline shows graceful skeleton state"
```

---

## Completion Checklist

- [ ] `next.config.js` has two rewrites: `/api/gold/*` → port 8000, `/api/forex/*` → port 8001
- [ ] `dashboard/context/BotContext.tsx` exports `BotProvider`, `useBot`, `BotId`
- [ ] `dashboard/lib/api.ts` — all 9 exported functions accept `bot` as first parameter
- [ ] `dashboard/components/BotTabSwitcher.tsx` renders GOLD / FOREX pill tabs with correct colors
- [ ] `dashboard/app/layout.tsx` wraps children with `BotProvider`
- [ ] `dashboard/app/page.tsx` uses `useBot()` and passes `bot` to all fetch calls
- [ ] `dashboard/components/StatusBar.tsx` includes `BotTabSwitcher`
- [ ] `npx tsc --noEmit` in dashboard/ reports zero TypeScript errors
- [ ] Switching tabs in browser correctly switches data source
