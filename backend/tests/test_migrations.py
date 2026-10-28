"""Migration assets and operational script safety checks."""

import sys
from pathlib import Path

import pytest
from scripts import apply_migrations

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def test_phase_three_migration_exists_and_is_version_named() -> None:
    files = migration_files()

    assert files
    assert all(apply_migrations._MIGRATION_NAME.fullmatch(path.name) for path in files)


def test_migration_defines_tables_relationships_and_financial_constraints() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8") for path in migration_files())

    assert "create table if not exists public.events" in sql
    assert "create table if not exists public.event_budgets" in sql
    assert "create table if not exists public.budget_expenses" in sql
    assert "event_id uuid not null unique" in sql
    assert "references public.events (id) on delete cascade" in sql
    assert "references public.event_budgets (id) on delete cascade" in sql
    assert "numeric(12, 2)" in sql
    assert "amount > 0" in sql
    assert "amount_status in ('estimated', 'quoted', 'confirmed')" in sql
    assert "reserve_type in ('percentage', 'fixed_amount')" in sql
    assert "reserve_value <= total_limit" in sql


def test_migration_prepares_rls_and_owner_scoped_policies() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8") for path in migration_files())

    assert sql.count("enable row level security") >= 3
    assert "owner_id uuid references auth.users" in sql
    assert "events_owner_select" in sql
    assert "event_budgets_owner_all" in sql
    assert "budget_expenses_owner_all" in sql
    assert "auth.uid()" in sql


def test_planning_proposals_migration_is_owner_scoped_and_advisory() -> None:
    sql = (MIGRATIONS_DIR / "202610250001_planning_proposals.sql").read_text(encoding="utf-8")

    assert "create table if not exists public.planning_proposals" in sql
    assert "proposal_type in ('ai_planning')" in sql
    assert "status in (" in sql
    assert "jsonb_typeof(payload) = 'object'" in sql
    assert "version integer not null" in sql
    assert "planning_proposals_owner_all" in sql
    assert "owner_id = auth.uid()" in sql
    assert "enable row level security" in sql


def test_migration_uses_non_reserved_constraint_column_name() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8") for path in migration_files())

    assert "event_constraints jsonb" in sql
    assert "owner_id is reserved" in sql


def test_migration_checksum_is_line_ending_independent(tmp_path: Path) -> None:
    lf_file = tmp_path / "lf.sql"
    crlf_file = tmp_path / "crlf.sql"
    lf_file.write_bytes(b"create table example (id int);\n")
    crlf_file.write_bytes(b"create table example (id int);\r\n")

    assert apply_migrations._sha256(lf_file) == apply_migrations._sha256(crlf_file)


def test_migration_script_exits_safely_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SUPABASE_DB_URL", "")
    monkeypatch.setattr(sys, "argv", ["apply_migrations.py"])

    exit_code = apply_migrations.main()

    assert exit_code == 2
    assert "SUPABASE_DB_URL is not configured" in capsys.readouterr().err


def test_migration_script_rejects_invalid_filenames_before_connecting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "not-a-migration.sql").write_text("select 1;", encoding="utf-8")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://user:password@localhost/test")
    monkeypatch.setattr(
        sys,
        "argv",
        ["apply_migrations.py", "--migrations-dir", str(tmp_path)],
    )

    exit_code = apply_migrations.main()

    assert exit_code == 2
    assert "Invalid migration filenames" in capsys.readouterr().err
