# OpenGold — AI-Powered Forex & Gold Trading Bot

Automated trading system for **XAUUSD (Gold)** and **GBPUSD (Forex)** using MetaTrader 5, Claude AI, and a Next.js live dashboard.

---

## Architecture

```
MT5 Terminal
    │
    ▼
main.py (Trading Bot)   ──►  src/api/app.py (FastAPI)  ──►  dashboard/ (Next.js)
    │                                │
    ▼                                ▼
PostgreSQL (TimescaleDB)  ◄──────────┘
```

**Two independent bots**, each with its own DB, API port, and config:

| Bot   | Symbol   | TF | Port | DB         |
|-------|----------|----|------|------------|
| Gold  | XAUUSDM  | M1 | 8000 | opengold   |
| Forex | GBPUSD   | M5 | 8001 | openforex  |

---

## Prerequisites

- **Windows** with MetaTrader 5 installed and logged in
- **Python 3.11+** with virtualenv
- **Node.js 18+** (for dashboard)
- **Docker Desktop** (for TimescaleDB) or a local PostgreSQL 15+
- **Anthropic API key**

---

## Quick Start

```powershell
# 1. Start everything with one click:
.\start_all.ps1
```

Or manually follow the steps below.

---

## Manual Setup

### 1. Database (TimescaleDB via Docker)

```powershell
# Start TimescaleDB container
docker-compose up -d

# Create databases and schema
$env:PGPASSWORD='opengold_local_pw'
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'

# Gold DB
& $psql -h localhost -U opengold -d opengold   -f src/schema.sql

# Forex DB (create it first, then apply schema)
& $psql -h localhost -U opengold -d postgres   -c "CREATE DATABASE openforex OWNER opengold;"
& $psql -h localhost -U opengold -d openforex  -f src/schema.sql
```

### 2. Python Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Config Files

Copy and edit the env files — **never commit real credentials**:

```
gold.env    ← MT5 login, DB, Anthropic key, risk params for Gold
forex.env   ← MT5 login, DB, Anthropic key, risk params for Forex
```

Key variables:

| Variable | Description |
|---|---|
| `MT5_LOGIN` | MT5 account number |
| `MT5_PASSWORD` | MT5 password |
| `MT5_SERVER` | MT5 broker server |
| `DB_NAME` | PostgreSQL database name |
| `ANTHROPIC_API_KEY` | Claude API key |
| `RISK_PER_TRADE` | Fraction of balance risked per trade (e.g. `0.002`) |
| `SYMBOL` | MT5 symbol (e.g. `XAUUSDM`, `GBPUSD`) |
| `API_PORT` | FastAPI port (8000 for gold, 8001 for forex) |

### 4. Preflight Check

```powershell
# Gold
.\.venv\Scripts\python.exe preflight.py

# Forex
.\.venv\Scripts\python.exe preflight.py --env forex.env
```

### 5. Start APIs

```powershell
# Gold API (Terminal 1)
uvicorn src.api.app:app --host 127.0.0.1 --port 8000

# Forex API (Terminal 2)
$env:ENV_FILE='forex.env'; uvicorn src.api.app:app --host 127.0.0.1 --port 8001
```

### 6. Start Bots

```powershell
# Gold Bot (Terminal 3)
python main.py

# Forex Bot (Terminal 4)
python main.py --env forex.env
```

### 7. Dashboard

```powershell
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

---

## Strategy Pipeline

Each candle tick runs all 13 strategies simultaneously:

| # | Strategy | Type |
|---|----------|------|
| 1 | RSI | Oscillator |
| 2 | MACD | Trend/Momentum |
| 3 | Bollinger Bands | Mean Reversion |
| 4 | Ichimoku Cloud | Trend |
| 5 | ADX Trend | Trend Strength |
| 6 | Momentum | Momentum |
| 7 | Scalping | Short-Term |
| 8 | Stochastic | Oscillator |
| 9 | MA Crossover | Trend |
| 10 | Mean Reversion | Oscillator |
| 11 | Breakout | Breakout |
| 12 | Support/Resistance | Structure |
| 13 | VWAP | Intraday |

**Decision flow:**
1. Strategies vote → weighted aggregate score (regime-aware)
2. Trigger gate: `max(buy, sell) ≥ threshold` AND `|buy − sell| ≥ min_diff`
3. Claude AI reviews journal + scores → BUY / SELL / SKIP + SL/TP
4. Risk engine validates: confidence, R:R ratio, daily drawdown, kill switch
5. MT5 order placed (or simulated in `DRY_RUN=true`)

---

## Risk Controls

- **Per-trade risk**: configurable `RISK_PER_TRADE` (% of balance)
- **Daily drawdown limit**: halts trading if exceeded
- **Max concurrent trades**: hard cap per bot
- **Kill switch**: toggle from dashboard, auto-resets at UTC midnight
- **Position manager**: trailing stop-loss, breakeven, AI re-evaluation

---

## Dashboard Features

- Live price chart (lightweight-charts)
- Equity curve + performance grade (A–F)
- Win rate, Profit Factor, Max Drawdown, Expectancy
- Strategy signal breakdown + regime distribution
- Trades table with manual **Sync** button
- Risk Calculator modal (capital + leverage → lot size scenarios)
- Kill switch toggle
- EN / TH language switcher

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Project Structure

```
main.py              ← Trading bot entry point
preflight.py         ← Pre-launch checks
gold.env / forex.env ← Bot configs (not committed)
requirements.txt
docker-compose.yml   ← TimescaleDB

src/
  config.py          ← Env-driven config
  db.py              ← DB connection pool
  schema.sql         ← Table definitions
  mt5_bridge/        ← MT5 connect, data, history
  strategies/        ← 13 independent strategies
  aggregator/        ← Weighted signal scoring
  regime/            ← Market regime classifier
  risk/              ← Risk validation engine
  executor/          ← Order placement + position manager
  ai_layer/          ← Claude prompt + client
  logger/            ← DB write helpers
  journal/           ← Trade history reader
  api/               ← FastAPI app + routes
  trigger/           ← Trigger gate logic

dashboard/           ← Next.js 14 frontend
  app/               ← Page layout
  components/        ← UI panels
  lib/               ← API client, i18n, bot-meta
```
