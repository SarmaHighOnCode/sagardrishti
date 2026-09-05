"""AIS recorder health check. Run daily for week 1, weekly after.

A recorder that silently stopped in October and is discovered in December
is the worst available outcome - AISStream has no replay, so that data is
gone forever. This is why this script exists: `make ais-status`.

Reads:
  - the recorder's own status file (SAGAR_AISD_STATUS_PATH, or
    --status-file), written by services/aisd after every flush attempt
  - Postgres directly (DATABASE_URL), for rows-in-24h and a gap report

Needs: psycopg[binary] (``uv pip install "psycopg[binary]"``). The status
file section still runs without it, degraded, so a missing driver doesn't
hide a recorder that has actually stopped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

DEFAULT_STATUS_PATH = os.environ.get("SAGAR_AISD_STATUS_PATH", "wal/aisd_status.json")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--status-file",
        default=DEFAULT_STATUS_PATH,
        help="Path to the recorder's status JSON (default: %(default)s)",
    )
    p.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="Postgres DSN (default: $DATABASE_URL)",
    )
    p.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Lookback window for the DB checks (default: %(default)s)",
    )
    return p.parse_args()


def report_status_file(path: str) -> bool:
    """Returns True if the status file looks healthy."""
    print(f"--- recorder status ({path}) ---")
    if not os.path.exists(path):
        print(
            "NOT FOUND. Either aisd has never run, or SAGAR_AISD_STATUS_PATH / "
            "--status-file points somewhere else than aisd's SAGAR_AISD_WAL_DIR."
        )
        return False

    with open(path, encoding="utf-8") as f:
        status = json.load(f)

    now = dt.datetime.now(dt.UTC)
    healthy = True

    last_msg = status.get("last_message_at")
    if last_msg:
        age = now - dt.datetime.fromisoformat(last_msg.replace("Z", "+00:00"))
        flag = "OK" if age < dt.timedelta(minutes=5) else "STALE"
        if flag == "STALE":
            healthy = False
        print(f"  last message:        {last_msg}  ({age} ago)  [{flag}]")
    else:
        print("  last message:        never")
        healthy = False

    print(f"  messages received:   {status.get('messages_received', 0)}")
    print(f"  positions persisted: {status.get('positions_persisted', 0)}")
    print(f"  statics persisted:   {status.get('statics_persisted', 0)}")
    print(f"  reconnects:          {status.get('reconnects', 0)}")

    dropped = status.get("rows_dropped_from_memory", 0)
    if dropped:
        print(
            f"  ROWS DROPPED FROM MEMORY: {dropped}  "
            f"(still in the WAL - needs a manual replay, see internal/wal)"
        )
        healthy = False

    last_err = status.get("last_flush_error")
    if last_err:
        print(f"  LAST FLUSH ERROR:    {last_err}")
        healthy = False

    return healthy


def report_database(database_url: str | None, hours: int) -> bool:
    print(f"\n--- database, last {hours}h ---")
    if not database_url:
        print("DATABASE_URL not set - skipping. Set it or pass --database-url.")
        return False

    try:
        import psycopg
    except ImportError:
        print('psycopg not installed - run: uv pip install "psycopg[binary]"')
        return False

    healthy = True
    with (
        psycopg.connect(database_url, connect_timeout=10) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT count(*) FROM ais_positions WHERE time > now() - %s::interval",
            (f"{hours} hours",),
        )
        total = cur.fetchone()[0]
        print(f"  rows recorded:       {total}")
        if total == 0:
            healthy = False

        cur.execute(
            """
            SELECT aoi, count(*), count(*) FILTER (WHERE data_quality = 'unreliable')
            FROM ais_positions
            WHERE time > now() - %s::interval
            GROUP BY aoi
            ORDER BY aoi
            """,
            (f"{hours} hours",),
        )
        for aoi, count, unreliable in cur.fetchall():
            pct = (unreliable / count * 100) if count else 0
            print(f"    {aoi:<15} {count:>8} rows  ({unreliable} unreliable, {pct:.1f}%)")

        cur.execute(
            """
            SELECT max(gap) FROM (
                SELECT time - lag(time) OVER (ORDER BY time) AS gap
                FROM ais_positions
                WHERE time > now() - %s::interval
            ) t
            """,
            (f"{hours} hours",),
        )
        row = cur.fetchone()
        gap = row[0] if row else None
        print(f"  largest single gap:  {gap if gap is not None else 'n/a'}")
        if gap is not None and gap > dt.timedelta(hours=1):
            print(
                "  WARNING: gap over 1h suggests a connection drop that wasn't just backoff jitter."
            )
            healthy = False

    return healthy


def main() -> int:
    args = parse_args()
    status_ok = report_status_file(args.status_file)
    db_ok = report_database(args.database_url, args.hours)

    print()
    if status_ok and db_ok:
        print("OVERALL: OK")
        return 0
    print("OVERALL: NEEDS ATTENTION - see warnings above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
