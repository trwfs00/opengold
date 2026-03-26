export type Locale = 'en' | 'th'

export const translations = {
  en: {
    // StatusBar
    botAlive: 'BOT ALIVE',
    botOffline: 'BOT OFFLINE',
    dryRun: 'DRY RUN',
    killSwitchActive: '⚠ KILL SWITCH ACTIVE — Click to Resume',
    killSwitch: 'Kill Switch',

    // HeroPanel
    strategies: '13 strategies on M1 candles — every 1 min, 24/7.',
    nextAnalysis: 'Next Analysis',
    today: 'Today',
    wlhLabel: 'W / L / H',
    allTime: 'All-Time',
    decisions: 'decisions',
    discipline: 'Discipline',
    holdRate: 'hold rate',
    confluence: 'Confluence',
    avg: 'avg',

    // PerformancePanel
    performance: 'Performance',
    balance: 'Balance',
    equity: 'Equity',
    winRate: 'Win Rate',
    closed: 'Closed',
    avgRR: 'Avg R:R',
    streak: 'Streak',
    winStreak: 'win streak',
    lossStreak: 'loss streak',
    open: 'Open',
    totalPnL: 'Total P&L',
    lastNTrades: (n: number) => `Last ${n} Trades`,
    noClosedTrades: 'No closed trades yet.',
    openPositions: 'Open Positions',
    entry: 'Entry',
    now: 'Now',
    lot: 'lot',

    // SignalsPanel
    signals: 'Signals',
    loading: 'Loading...',
    regime: 'Regime',
    buyScore: 'Buy Score',
    sellScore: 'Sell Score',
    mt5Disconnected: 'MT5 DISCONNECTED',
    // Tooltip
    decisionPipeline: 'Decision Pipeline',
    triggerThreshold: 'Trigger threshold',
    minSeparation: 'Min separation',
    pipelineSteps: [
      { label: '13 Strategies', desc: '— RSI, MACD, VWAP, Bollinger, Ichimoku, ADX, Momentum, Scalping, Stochastic, MA Crossover, Mean Reversion, Breakout, S/R — run on M1 candles every minute.' },
      { label: 'Aggregator', desc: '— scores weighted by regime. TRENDING amplifies momentum/trend strategies. RANGING amplifies oscillators/mean-reversion.' },
      { label: 'Trigger gate', desc: '— fires when max(buy, sell) ≥ 4.0 and |buy − sell| ≥ 1.0. Only during London & NY sessions (09:00–12:00 & 13:00–17:00 UTC).' },
      { label: 'AI (Claude)', desc: '— reviews journal context, decides BUY/SELL/SKIP, sets SL & TP.' },
      { label: 'Risk validator', desc: '— checks confidence, R:R ratio, max concurrent trades, kill switch.' },
      { label: 'MT5 order', desc: '— placed live (or simulated in DRY_RUN mode).' },
    ],

    // Pagination
    pageOf: (cur: number, total: number) => `${cur} / ${total}`,
    prevPage: 'Prev',
    nextPage: 'Next',

    // Model pricing tooltip
    modelPricingTitle: 'AI Cost per Decision',
    modelPricingInput: 'Input',
    modelPricingOutput: 'Output',
    modelPricingCost: 'Cost / decision',
    modelPricingBudget: (n: number) => `$${n} budget → ~${Math.round(n / 0.00135).toLocaleString()} decisions`,
    modelPricingNote: 'Prices from Anthropic API',

    // DecisionsTable
    decisionsTitle: 'Decisions',
    rows: (n: number) => `${n} rows`,
    noDecisions: 'No decisions yet.',
    colTime: 'Time',
    colRegime: 'Regime',
    colBuy: 'Buy',
    colSell: 'Sell',
    colAction: 'Action',
    colConf: 'Conf.',
    colReason: 'Reason',

    // TradesTable
    tradesTitle: 'Trades',
    nClosed: (n: number) => `${n} closed`,
    colClosed: 'Closed',
    colDir: 'Dir',
    colLots: 'Lots',
    colOpen: 'Open',
    colClose: 'Close',
    colResult: 'Result',

    // AnalyticsPanel
    analyticsTitle: 'Strategy Analytics',
    strategiesSection: 'Strategies',
    regimeSection: 'Market Regime Distribution',
    underTheHoodSection: 'Under the Hood',
    totalDecisions: (n: number) => `${n} decisions sampled`,
    noStrategyData: 'No signal data yet.',
    noRegimeData: 'No regime history yet.',
    underTheHoodLines: [
      'M — 13 strategies vote on M1 candle data every minute.',
      'R — Regime detector weights votes: TRENDING boosts momentum/trend, RANGING boosts oscillators.',
      'P — Trigger gate filters noise; AI reviews context before placing any order.',
    ],
  },

  th: {
    // StatusBar
    botAlive: 'บอทออนไลน์',
    botOffline: 'บอทออฟไลน์',
    dryRun: 'ทดสอบ',
    killSwitchActive: '⚠ หยุดฉุกเฉิน — คลิกเพื่อกลับ',
    killSwitch: 'หยุดฉุกเฉิน',

    // HeroPanel
    strategies: '13 กลยุทธ์ บน M1 ทุก 1 นาที, 24/7.',
    nextAnalysis: 'วิเคราะห์ถัดไป',
    today: 'วันนี้',
    wlhLabel: 'ชนะ / แพ้ / ถือ',
    allTime: 'ตลอดกาล',
    decisions: 'การตัดสิน',
    discipline: 'วินัย',
    holdRate: 'อัตราถือ',
    confluence: 'สัญญาณรวม',
    avg: 'เฉลี่ย',

    // PerformancePanel
    performance: 'ผลการเทรด',
    balance: 'ยอดเงิน',
    equity: 'ทุนจริง',
    winRate: 'อัตราชนะ',
    closed: 'ปิดแล้ว',
    avgRR: 'R:R เฉลี่ย',
    streak: 'สตรีค',
    winStreak: 'ชนะต่อเนื่อง',
    lossStreak: 'แพ้ต่อเนื่อง',
    open: 'เปิดอยู่',
    totalPnL: 'P&L รวม',
    lastNTrades: (n: number) => `${n} เทรดล่าสุด`,
    noClosedTrades: 'ยังไม่มีเทรดที่ปิด',
    openPositions: 'สถานะที่เปิดอยู่',
    entry: 'เข้า',
    now: 'ตอนนี้',
    lot: 'ล็อต',

    // SignalsPanel
    signals: 'สัญญาณ',
    loading: 'กำลังโหลด...',
    regime: 'สภาวะตลาด',
    buyScore: 'คะแนนซื้อ',
    sellScore: 'คะแนนขาย',
    mt5Disconnected: 'MT5 ไม่เชื่อมต่อ',
    // Tooltip
    decisionPipeline: 'ขั้นตอนตัดสินใจ',
    triggerThreshold: 'เกณฑ์ทริกเกอร์',
    minSeparation: 'ต่างขั้นต่ำ',
    pipelineSteps: [
      { label: '13 กลยุทธ์', desc: '— RSI, MACD, VWAP, Bollinger, Ichimoku, ADX, Momentum, Scalping, Stochastic, MA Crossover, Mean Reversion, Breakout, S/R — รันบน M1 candle ทุก 1 นาที' },
      { label: 'ตัวรวมสัญญาณ', desc: '— คะแนนถ่วงน้ำหนักตามสภาวะตลาด TRENDING เน้นกลยุทธ์ momentum/trend, RANGING เน้น oscillator/mean-reversion' },
      { label: 'ประตูทริกเกอร์', desc: '— ทำงานเมื่อ max(ซื้อ, ขาย) ≥ 4.0 และ |ซื้อ − ขาย| ≥ 1.0 เฉพาะ London & NY session (09:00–12:00 & 13:00–17:00 UTC)' },
      { label: 'AI (Claude)', desc: '— ทบทวนบันทึก ตัดสินใจ BUY/SELL/SKIP, กำหนด SL & TP' },
      { label: 'ตรวจสอบความเสี่ยง', desc: '— ตรวจ confidence, R:R ratio, จำนวน trade สูงสุด, kill switch' },
      { label: 'คำสั่ง MT5', desc: '— เปิดจริง (หรือจำลองในโหมด DRY_RUN)' },
    ],

    // Pagination
    pageOf: (cur: number, total: number) => `${cur} / ${total}`,
    prevPage: 'ก่อน',
    nextPage: 'ถัดไป',

    // Model pricing tooltip
    modelPricingTitle: 'ค่าใช้จ่าย AI ต่อครั้ง',
    modelPricingInput: 'Input',
    modelPricingOutput: 'Output',
    modelPricingCost: 'ค่าใช้จ่าย / ครั้ง',
    modelPricingBudget: (n: number) => `งบ $${n} → ~${Math.round(n / 0.00135).toLocaleString()} ครั้ง`,
    modelPricingNote: 'ราคาจาก Anthropic API',

    // DecisionsTable
    decisionsTitle: 'การตัดสินใจ',
    rows: (n: number) => `${n} แถว`,
    noDecisions: 'ยังไม่มีการตัดสินใจ',
    colTime: 'เวลา',
    colRegime: 'สภาวะ',
    colBuy: 'ซื้อ',
    colSell: 'ขาย',
    colAction: 'คำสั่ง',
    colConf: 'ความมั่นใจ',
    colReason: 'เหตุผล',

    // TradesTable
    tradesTitle: 'เทรด',
    nClosed: (n: number) => `ปิดแล้ว ${n}`,
    colClosed: 'ปิด',
    colDir: 'ทิศ',
    colLots: 'ล็อต',
    colOpen: 'เข้า',
    colClose: 'ออก',
    colResult: 'ผล',

    // AnalyticsPanel
    analyticsTitle: 'วิเคราะห์กลยุทธ์',
    strategiesSection: 'กลยุทธ์',
    regimeSection: 'การกระจายสภาวะตลาด',
    underTheHoodSection: 'กลไกภายใน',
    totalDecisions: (n: number) => `${n} การตัดสินใจ`,
    noStrategyData: 'ยังไม่มีข้อมูลสัญญาณ',
    noRegimeData: 'ยังไม่มีประวัติสภาวะตลาด',
    underTheHoodLines: [
      'M — 13 กลยุทธ์โหวตจากข้อมูล M1 candle ทุก 1 นาที',
      'R — ตัวตรวจสภาวะถ่วงน้ำหนักโหวต: TRENDING เน้น momentum/trend, RANGING เน้น oscillator',
      'P — Trigger gate กรองสัญญาณรบกวน; AI ตรวจบริบทก่อนเปิด order ทุกครั้ง',
    ],
  },
} as const

export type T = typeof translations.en | typeof translations.th
