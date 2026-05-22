from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

from talent_intel_crm.db import get_connection


MIGRATIONS_DIR_CANDIDATES = [
    Path.cwd() / "sql",
    Path(__file__).resolve().parents[2] / "sql",
]


def _migration_files() -> list[Path]:
    for directory in MIGRATIONS_DIR_CANDIDATES:
        if directory.is_dir():
            return sorted(path for path in directory.glob("*.sql") if path.name[:4].isdigit())
    raise RuntimeError("SQL migration directory not found")


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_migration_table() -> None:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                create table if not exists ticrm_schema_migrations (
                    version text primary key,
                    checksum text not null,
                    applied_at timestamptz not null default now()
                )
                """
            )


def applied_migrations() -> dict[str, str]:
    ensure_migration_table()
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select version, checksum from ticrm_schema_migrations order by version")
            return {row["version"]: row["checksum"] for row in cur.fetchall()}


def migration_status() -> list[dict[str, Any]]:
    applied = applied_migrations()
    return [
        {
            "version": path.name,
            "checksum": _checksum(path),
            "applied": path.name in applied,
            "checksum_matches": path.name not in applied or applied[path.name] == _checksum(path),
        }
        for path in _migration_files()
    ]


def apply_pending_migrations() -> list[str]:
    applied = applied_migrations()
    completed = []
    for path in _migration_files():
        checksum = _checksum(path)
        existing_checksum = applied.get(path.name)
        if existing_checksum:
            if existing_checksum != checksum:
                raise RuntimeError(f"Migration checksum changed after apply: {path.name}")
            continue
        with get_connection() as connection:
            with connection.cursor() as cur:
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "insert into ticrm_schema_migrations (version, checksum) values (%s, %s)",
                    (path.name, checksum),
                )
        completed.append(path.name)
    return completed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Talent Intel CRM SQL migration runner")
    parser.add_argument("command", choices=["apply", "status"])
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "apply":
        print({"applied": apply_pending_migrations()})
    else:
        print({"migrations": migration_status()})


if __name__ == "__main__":
    main()
