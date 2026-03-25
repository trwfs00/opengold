#!/usr/bin/env python
"""OpenGold preflight check — run before launching main.py."""
import os
import sys
from dotenv import load_dotenv

REQUIRED_VARS = ["MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "DB_PASSWORD"]


def _ok(msg):
    print(f"[OK]   {msg}")


def _fail(msg):
    print(f"[FAIL] {msg}")


def _skip(msg):
    print(f"[SKIP] {msg}")


def _warn(msg):
    print(f"[WARN] {msg}")


def check_env() -> bool:
    load_dotenv()
    missing = [k for k in REQUIRED_VARS if not os.getenv(k)]
    if missing:
        for k in missing:
            _fail(f"Missing required env var: {k}")
        return False
    try:
        count = sum(1 for line in open(".env") if "=" in line and not line.strip().startswith("#"))
    except Exception:
        count = "?"
    _ok(f".env loaded ({count} variables)")
    return True


def check_db() -> bool:
    import psycopg2
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "opengold")
    user = os.getenv("DB_USER", "opengold")
    password = os.getenv("DB_PASSWORD")
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    except Exception as e:
        _fail(f"TimescaleDB: {e} — is docker-compose up?")
        return False
    _ok(f"TimescaleDB connected ({user}@{host}:{port})")
    required_tables = {"candles", "decisions", "trades", "system_state"}
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        existing = {row[0] for row in cur.fetchall()}
    conn.close()
    missing_tables = required_tables - existing
    if missing_tables:
        _fail(f"Missing tables: {', '.join(sorted(missing_tables))} — run schema.sql")
        return False
    _ok(f"Tables verified: {', '.join(sorted(required_tables))}")
    return True


def check_mt5() -> bool:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        _fail("MetaTrader5 package not installed")
        return False
    login = int(os.getenv("MT5_LOGIN", "0"))
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")
    if not mt5.initialize(login=login, password=password, server=server):
        _fail(f"MT5 initialize failed: {mt5.last_error()} — is MT5 terminal running?")
        return False
    info = mt5.account_info()
    mt5.shutdown()
    if info is None:
        _fail("MT5 connected but account_info() returned None")
        return False
    _ok(f"MT5 connected (account: {info.login}, server: {info.server})")
    return True


def check_dry_run():
    dry_run = os.getenv("DRY_RUN", "false").lower()
    if dry_run == "false":
        _warn("DRY_RUN=false — LIVE MODE, real orders will be placed")
    else:
        _ok("DRY_RUN=true — safe mode, no real orders")


def main():
    print()
    env_ok = check_env()
    if not env_ok:
        _skip("TimescaleDB check skipped (requires .env)")
        _skip("MT5 check skipped (requires .env)")
        check_dry_run()
        print("\n1 or more checks failed. Fix the above before launching.\n")
        sys.exit(1)

    db_ok = check_db()
    if not db_ok:
        _skip("MT5 check skipped (requires DB)")
        check_dry_run()
        print("\n1 check failed. Fix the above before launching.\n")
        sys.exit(1)

    mt5_ok = check_mt5()
    check_dry_run()

    if mt5_ok:
        print("\nAll checks passed. Ready to launch: python main.py\n")
        sys.exit(0)
    else:
        print("\n1 check failed. Fix the above before launching.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
