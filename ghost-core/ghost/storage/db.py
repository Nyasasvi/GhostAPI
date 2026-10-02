"""SQLite metadata store with versioned, checksummed, reversible migrations.

Migrations live in ``ghost/storage/migrations/NNNN_name.sql`` with a matching
``NNNN_name.down.sql``. Applied migrations record their checksum; a later mismatch (an
edited migration) is refused rather than silently tolerated.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_NAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up: str
    down: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256((self.up + "\n--down--\n" + self.down).encode()).hexdigest()


class MigrationError(RuntimeError):
    pass


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    found = []
    for path in sorted(directory.glob("*.sql")):
        match = _NAME.match(path.name)
        if match is None:
            continue
        down = path.with_name(path.name.replace(".sql", ".down.sql"))
        if not down.exists():
            raise MigrationError(f"{path.name} has no reverse migration")
        found.append(
            Migration(int(match.group(1)), match.group(2), path.read_text(), down.read_text())
        )
    versions = [m.version for m in found]
    if versions != list(range(1, len(found) + 1)):
        raise MigrationError(f"migration versions must be contiguous from 1, got {versions}")
    return found


class Database:
    def __init__(self, path: Path | str, migrations_dir: Path = MIGRATIONS_DIR) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._migrations = load_migrations(migrations_dir)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL,"
            " applied_at TEXT NOT NULL)"
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise
        self.connection.execute("COMMIT")

    def applied(self) -> dict[int, str]:
        rows = self.connection.execute("SELECT version, checksum FROM schema_migrations")
        return {int(r["version"]): str(r["checksum"]) for r in rows}

    @property
    def schema_version(self) -> int:
        return max(self.applied(), default=0)

    def verify(self) -> None:
        known = {m.version: m for m in self._migrations}
        for version, checksum in self.applied().items():
            migration = known.get(version)
            if migration is None or migration.checksum != checksum:
                raise MigrationError(f"applied migration {version} was modified or removed")

    def migrate(self, target: int | None = None) -> int:
        self.verify()
        goal = len(self._migrations) if target is None else target
        current = self.schema_version
        if goal < current:
            for migration in reversed(self._migrations[goal:current]):
                with self.transaction() as conn:
                    _run_script(conn, migration.down)
                    conn.execute(
                        "DELETE FROM schema_migrations WHERE version = ?", (migration.version,)
                    )
            return self.schema_version
        for migration in self._migrations[current:goal]:
            with self.transaction() as conn:
                _run_script(conn, migration.up)
                conn.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
                    (migration.version, migration.name, migration.checksum, _now()),
                )
        return self.schema_version

    def close(self) -> None:
        self.connection.close()


def _run_script(conn: sqlite3.Connection, script: str) -> None:
    """Execute statements inside the caller's transaction (executescript would COMMIT)."""
    for statement in _split(script):
        conn.execute(statement)


def _split(script: str) -> list[str]:
    statements, buffer = [], []
    for line in script.splitlines():
        if line.strip().startswith("--"):
            continue
        buffer.append(line)
        joined = "\n".join(buffer).strip()
        if joined.endswith(";") and sqlite3.complete_statement(joined):
            statements.append(joined)
            buffer = []
    if "\n".join(buffer).strip():
        raise MigrationError("migration script ends with an incomplete statement")
    return statements


def _now() -> str:
    return datetime.now(UTC).isoformat()
