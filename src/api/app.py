from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.mt5_bridge.connection import connect, disconnect
from src.api.routes import candles, account, signals, decisions, trades, stats, status, killswitch, summary, regime_stats, position_events, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    connect()
    yield
    disconnect()


app = FastAPI(title="OpenGold API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(candles.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(killswitch.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(regime_stats.router, prefix="/api")
app.include_router(position_events.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
