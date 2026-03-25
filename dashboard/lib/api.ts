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
