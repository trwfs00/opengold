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
    strategies: (tf: string, min: number) => `13 strategies on ${tf} candles — every ${min} min, 24/7.`,
    nextAnalysis: 'Next Analysis',
    today: 'Today',
    wlhLabel: 'W / L / H',
    bshLabel: 'B / S / H',
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
    maxDrawdown: 'Max DD',
    profitFactor: 'Profit Factor',
    expectancy: 'Expectancy',
    perTrade: '/ trade',
    streak: 'Streak',

    // PerformanceSummaryModal
    perfModalTitle: 'Equity Curve & Bot Report',
    perfGradeLabel: 'Performance Grade',
    perfGradeA: 'Excellent — consistently profitable system',
    perfGradeB: 'Good — solid edge, keep monitoring',
    perfGradeC: 'Average — marginally profitable',
    perfGradeD: 'Below average — edge is weak',
    perfGradeF: 'Poor — net losing, needs review',
    perfGradeNA: 'Too few trades to grade reliably',
    perfAnalysis: 'Analysis',
    perfBulletWR: (pct: string, good: boolean) =>
      good
        ? `Win rate ${pct}% — bot wins the majority of trades`
        : `Win rate ${pct}% — below 50%; relies on R:R ratio to stay profitable`,
    perfBulletPF: (pf: string, tier: 'great' | 'ok' | 'bad') =>
      tier === 'great'
        ? `Profit factor ${pf} — for every $1 lost, $${pf} is earned back`
        : tier === 'ok'
        ? `Profit factor ${pf} — marginally positive; needs consistency`
        : `Profit factor ${pf} — losing more than earning`,
    perfBulletExp: (v: string, pos: boolean) =>
      pos
        ? `Average expected gain $${v} per trade — positive edge confirmed`
        : `Average expected loss $${v} per trade — no statistical edge yet`,
    perfBulletDD: (v: string, warn: boolean) =>
      warn
        ? `Max drawdown $${v} — notable drop from peak; consider reviewing lot sizing`
        : `Max drawdown $${v} — within acceptable range`,
    perfBulletCount: (n: number) =>
      n >= 30
        ? `${n} trades — statistically meaningful sample`
        : n >= 10
        ? `${n} trades — developing sample; results will stabilise over time`
        : `${n} trades — too few for reliable conclusions`,
    perfNoCurve: 'No closed trades yet — equity curve will appear here.',
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
    pipelineSteps: (tf: string, min: number) => [
      { label: '13 Strategies', desc: `— RSI, MACD, VWAP, Bollinger, Ichimoku, ADX, Momentum, Scalping, Stochastic, MA Crossover, Mean Reversion, Breakout, S/R — run on ${tf} candles every ${min} min.` },
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
    syncBtn: 'Sync',
    syncDone: (n: number) => n > 0 ? `+${n} synced` : 'Up to date',
    syncFail: 'Sync failed',

    // PositionEventsPanel
    posEventsTitle: 'Position Manager Log',
    posEventsEmpty: 'No position events yet.',
    posEventsTicket: 'Ticket',
    posEventsEvent: 'Event',
    posEventsPrice: 'Price',
    posEventsOldSL: 'Old SL',
    posEventsNewSL: 'New SL',
    posEventsReason: 'Reasoning',
    posEventsTrailBE: 'BREAKEVEN',
    posEventsTrailSL: 'TRAIL SL',
    posEventsReevalHold: 'HOLD',
    posEventsReevalClose: 'CLOSE',
    posEventsPartialClose: 'PARTIAL CLOSE',

    // RiskCalculator
    riskCalcBtn: 'Risk Check',
    riskCalcTitle: 'Risk Calculator',
    riskCalcSubtitle: (pct: string, sym: string) => `${sym} · ${pct}% risk per trade`,
    riskCalcCapital: 'Capital (USD)',
    riskCalcLeverage: 'Leverage',
    riskCalcLeverageOptional: '(optional)',
    riskCalcRiskPct: 'Risk / Trade',
    riskCalcDefault: 'default',
    riskCalcScenario: 'Scenario',
    riskCalcLot: 'Lot',
    riskCalcRisk: '$ Risk',
    riskCalcMargin: 'Margin',
    riskCalcMin: 'Min SL',
    riskCalcTypical: 'Typical',
    riskCalcMax: 'Max SL',
    riskCalcEmpty: 'Enter capital above to see risk analysis',
    riskCalcOkTitle: 'Capital is sufficient',
    riskCalcWarnTitle: 'Partial — only some SL ranges work',
    riskCalcFailTitle: (min: string) => `Too small — need ≥ $${min}`,
    riskCalcDrawdown: (n: number) => `Max ~${n} losing trades before −50% drawdown`,
    riskCalcMinLot: 'Lot size 0.01 is the minimum — capital too small',
    riskCalcHighLevWarn: (lev: number) => `High leverage — 1:${lev}`,
    riskCalcHighLevDesc: (pct: string) => `Margin req. is very low but losses scale the same way. A ${pct}% move against you wipes the margin.`,
    riskCalcFooter: (price: string, lev: string) => `Margin estimate uses live price (${price})${lev}`,
    riskCalcFooterNoLev: (price: string) => `Margin estimate uses live price (${price})`,

    // AnalyticsPanel
    analyticsTitle: 'Strategy Analytics',
    strategiesSection: 'Strategies',
    regimeSection: 'Market Regime Distribution',
    underTheHoodSection: 'Under the Hood',
    totalDecisions: (n: number) => `${n} decisions sampled`,
    noStrategyData: 'No signal data yet.',
    noRegimeData: 'No regime history yet.',
    underTheHoodLines: (tf: string, min: number) => [
      `M — 13 strategies vote on ${tf} candle data every ${min} min.`,
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
    strategies: (tf: string, min: number) => `13 กลยุทธ์ บน ${tf} ทุก ${min} นาที, 24/7.`,
    nextAnalysis: 'วิเคราะห์ถัดไป',
    today: 'วันนี้',
    wlhLabel: 'ชนะ / แพ้ / ถือ',
    bshLabel: 'ซื้อ / ขาย / ถือ',
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
    maxDrawdown: 'DD สูงสุด',
    profitFactor: 'Profit Factor',
    expectancy: 'Expectancy',
    perTrade: '/ ไม้',
    streak: 'สตรีค',

    // PerformanceSummaryModal
    perfModalTitle: 'กราฟ Equity & รายงานผลงานบอต',
    perfGradeLabel: 'เกรดผลงาน',
    perfGradeA: 'ยอดเยี่ยม — ทำกำไรได้อย่างสม่ำเสมอ',
    perfGradeB: 'ดี — เห็นความได้เปรียบชัดเจน',
    perfGradeC: 'พอใช้ได้ — ทำกำไรเล็กน้อย ยังปรับได้อีก',
    perfGradeD: 'ต่ำกว่าเกณฑ์ — edge ยังอ่อน',
    perfGradeF: 'ต้องปรับปรุง — ขาดทุนสุทธิ ต้องรีเวิวกลยุทธ์',
    perfGradeNA: 'ไม้เทรดยังน้อยเกินไป ยังไม่สามารถประเมินได้',
    perfAnalysis: 'วิเคราะห์',
    perfBulletWR: (pct: string, good: boolean) =>
      good
        ? `อัตราชนะ ${pct}% — บอตชนะมากกว่าแพ้`
        : `อัตราชนะ ${pct}% — ต่ำกว่า 50% ต้องพึ่งอัตรา R:R ทดแทน`,
    perfBulletPF: (pf: string, tier: 'great' | 'ok' | 'bad') =>
      tier === 'great'
        ? `Profit factor ${pf} — ชนะ $${pf} ต่อทุก $1 ที่เสีย`
        : tier === 'ok'
        ? `Profit factor ${pf} — ทำกำไรเล็กน้อย ต้องติดตามต่อเนื่อง`
        : `Profit factor ${pf} — เสียมากกว่าชนะ`,
    perfBulletExp: (v: string, pos: boolean) =>
      pos
        ? `คาดแนวทำกำไรเฉลี่ย $${v} ต่อไม้ — ยืนยันว่ามี edge จริง`
        : `คาดแนวขาดทุน $${v} ต่อไม้ — ยังไม่มี edge ทางสถิติ`,
    perfBulletDD: (v: string, warn: boolean) =>
      warn
        ? `Max drawdown $${v} — ถอยใหญ่จาก peak ควรตรวจขนาด lot`
        : `Max drawdown $${v} — อยู่ในระดับที่ยอมรับได้`,
    perfBulletCount: (n: number) =>
      n >= 30
        ? `เทรดแล้ว ${n} ไม้ — ข้อมูลเพียงพอทางสถิติแล้ว`
        : n >= 10
        ? `เทรดแล้ว ${n} ไม้ — กำลังสะสมข้อมูล ผลจะน่าเชื่อถือมากขึ้นเรื่อยๆ`
        : `เทรดแค่ ${n} ไม้ — ยังน้อยเกินไปสำหรับข้อสรุปที่แม่นยำ`,
    perfNoCurve: 'ยังไม่มีเทรดที่ปิด — กราฟจะแสดงที่นี่',
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
    pipelineSteps: (tf: string, min: number) => [
      { label: '13 กลยุทธ์', desc: `— RSI, MACD, VWAP, Bollinger, Ichimoku, ADX, Momentum, Scalping, Stochastic, MA Crossover, Mean Reversion, Breakout, S/R — รันบน ${tf} candle ทุก ${min} นาที` },
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
    syncBtn: 'ซิงค์',
    syncDone: (n: number) => n > 0 ? `+${n} ไม้` : 'อัปเดตแล้ว',
    syncFail: 'ซิงค์ล้มเหลว',

    // PositionEventsPanel
    posEventsTitle: 'บันทึก Position Manager',
    posEventsEmpty: 'ยังไม่มีการทำงาน',
    posEventsTicket: 'ตั๋ว',
    posEventsEvent: 'เหตุการณ์',
    posEventsPrice: 'ราคา',
    posEventsOldSL: 'SL เดิม',
    posEventsNewSL: 'SL ใหม่',
    posEventsReason: 'เหตุผล',
    posEventsTrailBE: 'BREAKEVEN',
    posEventsTrailSL: 'TRAIL SL',
    posEventsReevalHold: 'HOLD',
    posEventsReevalClose: 'CLOSE',
    posEventsPartialClose: 'ปิดบางส่วน',

    // RiskCalculator
    riskCalcBtn: 'เช็คความเสี่ยง',
    riskCalcTitle: 'คำนวณความเสี่ยง',
    riskCalcSubtitle: (pct: string, sym: string) => `${sym} · เสี่ยง ${pct}% ต่อไม้`,
    riskCalcCapital: 'ทุน (USD)',
    riskCalcLeverage: 'เลเวอเรจ',
    riskCalcLeverageOptional: '(ถ้ามี)',
    riskCalcRiskPct: 'ความเสี่ยง / ไม้',
    riskCalcDefault: 'ค่าเริ่มต้น',
    riskCalcScenario: 'สถานการณ์',
    riskCalcLot: 'ล็อต',
    riskCalcRisk: '$ เสี่ยง',
    riskCalcMargin: 'มาร์จิน',
    riskCalcMin: 'SL ต่ำสุด',
    riskCalcTypical: 'ปกติ',
    riskCalcMax: 'SL สูงสุด',
    riskCalcEmpty: 'กรอกทุนด้านบนเพื่อดูการวิเคราะห์ความเสี่ยง',
    riskCalcOkTitle: 'ทุนเพียงพอ',
    riskCalcWarnTitle: 'บางส่วนเท่านั้น — ได้เฉพาะบาง SL',
    riskCalcFailTitle: (min: string) => `ทุนน้อยเกินไป — ต้องมีอย่างน้อย $${min}`,
    riskCalcDrawdown: (n: number) => `แพ้ติดต่อกันสูงสุด ~${n} ไม้ก่อนขาดทุน 50%`,
    riskCalcMinLot: 'ล็อตขั้นต่ำคือ 0.01 — ทุนน้อยเกินไป',
    riskCalcHighLevWarn: (lev: number) => `เลเวอเรจสูง — 1:${lev}`,
    riskCalcHighLevDesc: (pct: string) => `ต้องการมาร์จินต่ำมาก แต่ความเสี่ยงเท่าเดิม ราคาขยับ ${pct}% ทิศทางตรงข้าม มาร์จินหมด`,
    riskCalcFooter: (price: string, lev: string) => `ใช้ราคาปัจจุบัน (${price})${lev}`,
    riskCalcFooterNoLev: (price: string) => `ใช้ราคาปัจจุบัน (${price})`,

    // AnalyticsPanel
    analyticsTitle: 'วิเคราะห์กลยุทธ์',
    strategiesSection: 'กลยุทธ์',
    regimeSection: 'การกระจายสภาวะตลาด',
    underTheHoodSection: 'กลไกภายใน',
    totalDecisions: (n: number) => `${n} การตัดสินใจ`,
    noStrategyData: 'ยังไม่มีข้อมูลสัญญาณ',
    noRegimeData: 'ยังไม่มีประวัติสภาวะตลาด',
    underTheHoodLines: (tf: string, min: number) => [
      `M — 13 กลยุทธ์โหวตจากข้อมูล ${tf} candle ทุก ${min} นาที`,
      'R — ตัวตรวจสภาวะถ่วงน้ำหนักโหวต: TRENDING เน้น momentum/trend, RANGING เน้น oscillator',
      'P — Trigger gate กรองสัญญาณรบกวน; AI ตรวจบริบทก่อนเปิด order ทุกครั้ง',
    ],
  },
} as const

export type T = typeof translations.en | typeof translations.th
