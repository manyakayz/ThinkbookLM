"""
Helper script to associate legacy pre-authentication records with a user account.

Usage (from backend/ directory):
    python -m scripts.claim_legacy_data --email user@example.com
    python -m scripts.claim_legacy_data --status
"""
from __future__ import annotations

import argparse
import sys
import psycopg

from app.config import get_settings


def claim_data(email: str | None = None, status_only: bool = False) -> None:
    settings = get_settings()

    with psycopg.connect(settings.postgres_dsn) as conn:
        # Check unassociated records
        unowned_nb = conn.execute("SELECT COUNT(*) FROM notebooks WHERE user_id IS NULL").fetchone()[0]
        unowned_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE user_id IS NULL").fetchone()[0]

        if status_only:
            print(f"Legacy records without user ownership:")
            print(f"  Notebooks: {unowned_nb}")
            print(f"  Documents: {unowned_docs}")
            return

        if not email:
            print("Error: --email must be specified to assign records.", file=sys.stderr)
            sys.exit(1)

        user_row = conn.execute("SELECT id, full_name, email FROM users WHERE email = %s", (email.strip().lower(),)).fetchone()
        if not user_row:
            print(f"Error: User with email '{email}' not found.", file=sys.stderr)
            sys.exit(1)

        user_id = user_row[0]
        user_name = user_row[1]

        if unowned_nb == 0 and unowned_docs == 0:
            print("No unassigned legacy records to claim.")
            return

        with conn.transaction():
            res_nb = conn.execute(
                "UPDATE notebooks SET user_id = %s WHERE user_id IS NULL",
                (user_id,),
            )
            res_doc = conn.execute(
                "UPDATE documents SET user_id = %s WHERE user_id IS NULL",
                (user_id,),
            )

        print(f"Successfully assigned to {user_name} ({email}, id={user_id}):")
        print(f"  {res_nb.rowcount} notebook(s)")
        print(f"  {res_doc.rowcount} document(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Associate legacy unowned records with an account.")
    parser.add_argument("--email", type=str, help="Email of the user account to own legacy data.")
    parser.add_argument("--status", action="store_true", help="Display count of unassociated legacy records.")
    args = parser.parse_args()

    claim_data(email=args.email, status_only=args.status)
