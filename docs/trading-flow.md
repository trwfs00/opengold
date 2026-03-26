# OpenGold — Trading Flow

> อัปเดต: March 25, 2026 | Timeframe: M1 | Symbol: XAUUSD

---

## Diagram

```mermaid
flowchart TD
    A([🕐 ทุก 1 นาที\nM1 candle ใหม่]) --> B[fetch_candles\nXAUUSD M1 × 200 แท่ง]

    B --> C{candles\nว่างเปล่า?}
    C -- ใช่ --> D{MT5\nเชื่อมต่อ?}
    D -- ไม่ --> E[reconnect_with_retry\nmax 3 ครั้ง]
    E --> A
    D -- ใช่\nตลาดปิด --> A

    C -- ไม่ --> F{candle time\n== last time?}
    F -- ใช่ already processed --> A
    F -- ไม่ ใหม่ --> G[classify_regime\nTRENDING / RANGING / CHOPPY]

    G --> H[run_all — 13 กลยุทธ์\nRSI · MACD · VWAP · Bollinger\nIchimoku · ADX · Momentum · Scalping\nStochastic · MA Crossover\nMean Reversion · Breakout · S/R]

    H --> I[compute_agg\nถ่วงน้ำหนักตาม regime\n→ buy_score / sell_score 0–10]

    I --> J[(log_decision DB\ntrigger_fired = false)]

    I --> K{Trigger Gate}
    K -- kill_switch active --> STOP1([🛑 หยุด])
    K -- open_trades ≥ 3 --> STOP2([🛑 หยุด])
    K -- max score < 5.0 --> STOP3([✋ ส่วนใหญ่จบที่นี่\nscore ปัจจุบัน ~2.4])
    K -- diff < 2.0 --> STOP4([🛑 หยุด])

    K -- ✅ ผ่านทั้งหมด --> L[build_prompt\njournal + price + ATR-14]

    L --> M{🤖 Claude Haiku\nclaude-3-5-haiku-20241022\nmax_tokens 256}
    M -- API error --> N[Fallback: Claude Sonnet\nclaude-3-5-sonnet-20241022]
    N -- error --> SKIP1([⏭ SKIP])

    M --> O{action?}
    N --> O
    O -- SKIP --> SKIP2([⏭ บันทึก AI_SKIP])
    O -- BUY/SELL --> P[Risk Validator]

    P --> Q{ตรวจสอบ}
    Q -- confidence < 0.65 --> R1([🚫 LOW_CONFIDENCE])
    Q -- SL < $3 หรือ > $50 --> R2([🚫 INVALID_SL])
    Q -- open_trades ≥ 3 --> R3([🚫 MAX_TRADES])

    Q -- ✅ ผ่าน --> S[คำนวณ lot size\nlot = balance×1% ÷ sl_dist×100]

    S --> T{DRY_RUN?}
    T -- true --> U([📝 Log เฉยๆ\nไม่ส่ง order])
    T -- false --> V[place_order MT5\nmarket order @ ask/bid\n+ SL + TP]

    V --> W{result.retcode\n== DONE?}
    W -- ไม่ --> X([❌ ORDER_REJECTED])
    W -- ใช่ --> Y([✅ ออเดอร์เปิดแล้ว\nticket บันทึก DB])

    Y --> Z[MT5 จัดการปิดอัตโนมัติ\nเมื่อราคาถึง SL หรือ TP]
    Z --> ZZ[sync_positions detect\nposition หายไป → log_trade DB]

    style A fill:#1c1917,stroke:#f59e0b,color:#fbbf24
    style M fill:#1e3a5f,stroke:#60a5fa,color:#93c5fd
    style N fill:#1e3a5f,stroke:#60a5fa,color:#93c5fd
    style Y fill:#14532d,stroke:#4ade80,color:#86efac
    style Z fill:#14532d,stroke:#4ade80,color:#86efac
    style STOP3 fill:#431407,stroke:#f97316,color:#fdba74
```

---

## ขั้นตอนทีละ Step

| # | ขั้นตอน | ไฟล์ | รายละเอียด |
|---|---------|------|------------|
| 1 | **Fetch Candles** | `src/mt5_bridge/data.py` | ดึง M1 × 200 แท่ง จาก MT5 |
| 2 | **Regime Classifier** | `src/regime/classifier.py` | TRENDING / RANGING / CHOPPY |
| 3 | **13 Strategies** | `src/strategies/` | แต่ละตัวส่งกลับ `{ signal, confidence }` |
| 4 | **Aggregator** | `src/aggregator/scorer.py` | รวม + ถ่วงน้ำหนักตาม regime → `buy_score`, `sell_score` |
| 5 | **Trigger Gate** | `src/trigger/gate.py` | `max(buy,sell) ≥ 5.0` **และ** `\|buy−sell\| ≥ 2.0` |
| 6 | **Build Prompt** | `src/ai_layer/prompt.py` | รวม journal context + price + ATR(14) |
| 7 | **Claude Haiku** ← AI เริ่มทำงาน | `src/ai_layer/client.py` | Primary: `claude-3-5-haiku-20241022` → JSON: `{ action, confidence, sl, tp }` |
| 8 | **Fallback Sonnet** | `src/ai_layer/client.py` | fallback เมื่อ Haiku error → `claude-3-5-sonnet-20241022` |
| 9 | **Risk Validator** | `src/risk/engine.py` | confidence ≥ 0.65, SL $3–$50, lot = balance×1% ÷ sl_dist×100 |
| 10 | **Place Order** | `src/executor/orders.py` | market order ส่ง MT5 พร้อม SL + TP |
| 11 | **MT5 Auto-Close** | MT5 engine | MT5 ปิด position เองเมื่อถึง SL/TP |
| 12 | **Sync & Log** | `main.py` → `src/logger/writer.py` | `sync_positions()` detect ว่า position หายไป → `log_trade()` DB |

---

## Thresholds (config defaults)

| Parameter | ค่า |
|-----------|-----|
| `TRIGGER_MIN_SCORE` | **5.0** |
| `TRIGGER_MIN_SCORE_DIFF` | **2.0** |
| `MIN_AI_CONFIDENCE` | **0.65** (65%) |
| `MIN_SL_USD` | **$3.00** |
| `MAX_SL_USD` | **$50.00** |
| `RISK_PER_TRADE` | **1%** ของ balance |
| `MAX_CONCURRENT_TRADES` | **3** |
| `POLL_INTERVAL_SECONDS` | **5 วินาที** (loop check) |
| Claude Primary | `claude-3-5-haiku-20241022` |
| Claude Fallback | `claude-3-5-sonnet-20241022` |

---

## สถานะปัจจุบัน (March 25, 2026)

- Bot ทำงานอยู่ สแกนทุก 1 นาที
- `buy_score` สูงสุดที่พบ: **~2.4** (ต้องการ ≥ 5.0)
- Trigger Gate: **ยังไม่เคยผ่าน** → Claude Haiku ยังไม่เคยถูกเรียก
- จำนวน decisions ใน DB: **101 rows** (ทั้งหมด trigger_fired = false)
