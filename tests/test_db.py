from src.db import get_connection


def test_db_connects():
    conn = get_connection()
    assert conn is not None
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
    assert result == (1,)
    conn.close()


def test_system_state_seeded():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT key FROM system_state ORDER BY key")
        keys = [row[0] for row in cur.fetchall()]
    conn.close()
    assert "kill_switch_active" in keys
    assert "daily_start_balance" in keys
    assert "daily_start_date" in keys
    assert "kill_switch_date" in keys
