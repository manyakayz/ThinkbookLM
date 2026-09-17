"""
Minimal migration runner.

This project uses raw SQL (see backend/app/services/db.py -- no ORM), so
migrations are plain `.sql` files in `backend/migrations/`, applied in
filename order and tracked in a `schema_migrations` table. This intentionally
avoids pulling in Alembic (which brings SQLAlchemy along as a dependency)
for what is, for now, a handful of straightforward DDL files.

Usage (from the backend/ directory, with the venv active):

    python -m scripts.migrate            # apply any pending migrations
    python -m scripts.migrate --status   # list applied / pending migrations, apply nothing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _ensure_tracking_table(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename    TEXT PRIMARY KEY,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    conn.commit()


def _applied_migrations(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute("SELECT filename FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def _all_migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def run(status_only: bool = False) -> None:
    settings = get_settings()
    files = _all_migration_files()

    if not files:
        print(f"No migration files found in {MIGRATIONS_DIR}")
        return

    with psycopg.connect(settings.postgres_dsn) as conn:
        _ensure_tracking_table(conn)
        applied = _applied_migrations(conn)

        pending = [f for f in files if f.name not in applied]

        if status_only:
            for f in files:
                marker = "applied" if f.name in applied else "pending"
                print(f"  [{marker:7}] {f.name}")
            return

        if not pending:
            print("Database is up to date -- no pending migrations.")
            return

        for f in pending:
            print(f"Applying {f.name} ...")
            sql = f.read_text(encoding="utf-8")
            try:
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (f.name,),
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"Migration {f.name} failed: {exc}", file=sys.stderr)
                raise SystemExit(1) from exc
            print(f"  applied {f.name}")

        print(f"Applied {len(pending)} migration(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply pending SQL migrations.")
    parser.add_argument("--status", action="store_true", help="Show applied/pending migrations without applying.")
    args = parser.parse_args()
    run(status_only=args.status)
