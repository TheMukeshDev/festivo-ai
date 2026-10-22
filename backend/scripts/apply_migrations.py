"""Apply versioned SQL migrations to the configured Supabase PostgreSQL database."""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"
ENV_FILE = BACKEND_DIR / ".env"

_MIGRATION_NAME = re.compile(r"^[0-9]{12}_[a-z0-9_]+\.sql$")
_TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version text PRIMARY KEY,
    checksum text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


class MigrationMismatchError(Exception):
    """An applied migration file was edited after it was recorded."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply pending Supabase SQL migrations transactionally."
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=DEFAULT_MIGRATIONS_DIR,
        help=f"Directory containing migration files (default: {DEFAULT_MIGRATIONS_DIR}).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    load_dotenv(ENV_FILE)
    dsn = os.getenv("SUPABASE_DB_URL", "").strip()
    if not dsn:
        print("SUPABASE_DB_URL is not configured; no migrations were applied.", file=sys.stderr)
        return 2

    try:
        timeout = int(os.getenv("SUPABASE_DB_CONNECT_TIMEOUT_SECONDS", "10"))
    except ValueError:
        print("SUPABASE_DB_CONNECT_TIMEOUT_SECONDS must be an integer.", file=sys.stderr)
        return 2

    migrations_dir: Path = args.migrations_dir
    if not migrations_dir.is_dir():
        print(f"Migration directory not found: {migrations_dir}", file=sys.stderr)
        return 2

    migrations = sorted(migrations_dir.glob("*.sql"))
    invalid_names = [path.name for path in migrations if not _MIGRATION_NAME.fullmatch(path.name)]
    if invalid_names:
        print(f"Invalid migration filenames: {', '.join(invalid_names)}", file=sys.stderr)
        return 2

    pending: list[Path] = []
    applied_now: list[str] = []
    try:
        with (
            psycopg.connect(dsn, connect_timeout=timeout, row_factory=dict_row) as connection,
            connection.cursor() as cursor,
            connection.transaction(),
        ):
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('festivo_ai_migrations'))")
            cursor.execute(_TRACKING_TABLE_SQL)
            cursor.execute("SELECT version, checksum FROM public.schema_migrations")
            applied = {row["version"]: row["checksum"] for row in cursor.fetchall()}

            for path in migrations:
                prior_checksum = applied.get(path.name)
                if prior_checksum is None:
                    pending.append(path)
                elif prior_checksum != _sha256(path):
                    raise MigrationMismatchError(
                        f"Migration {path.name} changed after it was applied."
                    )

            for path in pending:
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    """
                    INSERT INTO public.schema_migrations (version, checksum)
                    VALUES (%s, %s)
                    """,
                    (path.name, _sha256(path)),
                )
                applied_now.append(path.name)
    except MigrationMismatchError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for version in applied_now:
        print(f"Applied {version}")
    if not pending:
        print("No pending migrations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
