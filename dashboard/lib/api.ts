const BASE = (bot: 'gold' | 'forex') => `/api/${bot}`

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
  sl: number
  tp: number
  open_time: string
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
  ai_reasoning: string | null
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
  win_rate: number | null | undefined
  total_pnl: number | null | undefined
  avg_win: number | null | undefined
  avg_loss: number | null | undefined
  pnl_curve: PnlPoint[]
  win_count: number
  loss_count: number
  total_trades: number
  current_streak: number
  avg_rr: number | null | undefined
  last_15: string[]
}

export interface StatusData {
  bot_alive: boolean
  dry_run: boolean
  kill_switch_active: boolean
  ai_model?: string
  last_ai_time?: string
  ai_interval_minutes?: number
}

export interface SummaryData {
  today_win: number
  today_loss: number
  today_hold: number
  all_time_decisions: number
  discipline_hold_rate: number | null
  confluence_avg: number | null
}

export interface RegimeStats {
  stats: Record<string, { count: number; pct: number }>
  total: number
  error?: string
}

async function get<T>(path: string, bot: 'gold' | 'forex'): Promise<T> {
  const res = await fetch(`${BASE(bot)}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`)
  return res.json() as Promise<T>
}

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
