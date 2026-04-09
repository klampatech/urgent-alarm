#!/usr/bin/env python3
"""
Database Migration System for Urgent Alarm

Provides versioned SQLite migrations with:
- Sequential migration execution
- In-memory test mode support
- Foreign key enforcement
- WAL mode for performance
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
SCHEMA_VERSION_TABLE = "schema_version"


class DatabaseMigrationError(Exception):
    """Raised when migration fails."""
    pass


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database."""
    try:
        cursor = conn.execute(
            f"SELECT version FROM {SCHEMA_VERSION_TABLE} ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def ensure_version_table(conn: sqlite3.Connection) -> None:
    """Create schema version tracking table if not exists."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)


def get_migration_files() -> list[Tuple[int, str]]:
    """Get all migration files sorted by version."""
    migrations = []
    if not MIGRATIONS_DIR.exists():
        return migrations

    for file in MIGRATIONS_DIR.glob("*.sql"):
        # Extract version from filename (e.g., 001_initial_schema.sql -> 1)
        try:
            version = int(file.stem.split("_")[0])
            migrations.append((version, str(file)))
        except (ValueError, IndexError):
            continue

    return sorted(migrations, key=lambda x: x[0])


def parse_sql_file(sql_content: str) -> list[str]:
    """
    Parse SQL file into executable statements, handling comments and separators.

    Args:
        sql_content: Raw SQL file content

    Returns:
        List of executable SQL statements (one at a time)
    """
    statements = []
    current_lines = []

    for line in sql_content.split("\n"):
        # Strip the line
        stripped = line.strip()

        # Skip comment lines (both -- and # styles)
        if stripped.startswith("--") or stripped.startswith("#"):
            continue

        # Skip migration separators
        if stripped.startswith("---"):
            continue

        # Skip empty lines within statements
        if not stripped:
            continue

        # Add non-comment line to current statement
        current_lines.append(line)

        # If we hit a semicolon, this is the end of a statement
        if stripped.endswith(";"):
            stmt = "\n".join(current_lines)
            # Remove trailing semicolon for execution
            stmt = stmt.strip()
            if stmt.endswith(";"):
                stmt = stmt[:-1].strip()
            if stmt:
                statements.append(stmt)
            current_lines = []

    # Add any remaining statement without semicolon
    if current_lines:
        stmt = "\n".join(current_lines).strip()
        if stmt:
            statements.append(stmt)

    return statements


def run_migrations(
    db_path: str,
    in_memory: bool = False,
    target_version: Optional[int] = None
) -> int:
    """
    Run all pending migrations up to target_version.

    Args:
        db_path: Path to SQLite database
        in_memory: If True, use in-memory database
        target_version: If set, only migrate up to this version

    Returns:
        Final schema version after migrations

    Raises:
        DatabaseMigrationError: If migration fails
    """
    if in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        conn = sqlite3.connect(db_path)

    try:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Ensure version tracking table exists
        ensure_version_table(conn)

        # Get current version
        current_version = get_schema_version(conn)

        # Get all migration files
        migrations = get_migration_files()

        # Apply pending migrations
        for version, filepath in migrations:
            if version <= current_version:
                continue

            if target_version and version > target_version:
                break

            print(f"Applying migration {version:03d}...")

            # Read and execute migration
            with open(filepath, "r") as f:
                sql = f.read()

            # Parse SQL into statements
            statements = parse_sql_file(sql)

            for statement in statements:
                if statement:
                    conn.execute(statement)

            # Record migration
            conn.execute(
                f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, applied_at) VALUES (?, ?)",
                (version, datetime.utcnow().isoformat())
            )

            conn.commit()
            current_version = version
            print(f"  Applied migration {version:03d}")

        return current_version

    except Exception as e:
        conn.rollback()
        raise DatabaseMigrationError(f"Migration failed: {e}")

    finally:
        conn.close()


def init_database(
    db_path: str,
    in_memory: bool = False,
    reset: bool = False
) -> int:
    """
    Initialize database with migrations.

    Args:
        db_path: Path to SQLite database
        in_memory: If True, use in-memory database
        reset: If True, delete existing database first

    Returns:
        Final schema version
    """
    if reset and not in_memory:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Reset database: {db_path}")

    return run_migrations(db_path, in_memory=in_memory)


def get_connection(db_path: str, in_memory: bool = False) -> sqlite3.Connection:
    """
    Get a database connection with proper settings.

    Args:
        db_path: Path to SQLite database
        in_memory: If True, use in-memory database

    Returns:
        Configured sqlite3.Connection
    """
    if in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        conn = sqlite3.connect(db_path)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    return conn


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument(
        "--db-path",
        default="/tmp/urgent-alarm.db",
        help="Path to database file"
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="Use in-memory database"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before migrating"
    )
    parser.add_argument(
        "--version",
        type=int,
        help="Target version (migrate up to this version)"
    )

    args = parser.parse_args()

    version = init_database(
        args.db_path,
        in_memory=args.in_memory,
        reset=args.reset
    )

    print(f"Database initialized at version {version}")