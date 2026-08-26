#!/usr/bin/env python3
"""Validate the committed Stop-Motion Dictionary SQLite artifact."""

from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "limn_stop_motion_dictionary.sqlite"
EXPECTED_TERMS = 1077


def main() -> None:
    if not DATABASE.exists():
        raise SystemExit(f"Missing database: {DATABASE}")
    with sqlite3.connect(DATABASE) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise SystemExit(f"SQLite integrity check failed: {integrity}")
        terms = db.execute("SELECT COUNT(*) FROM terms").fetchone()[0]
        source_markdown = db.execute(
            "SELECT COUNT(*) FROM terms WHERE trim(source_markdown) <> ''"
        ).fetchone()[0]
        duplicates = db.execute(
            "SELECT COUNT(*) FROM (SELECT term_id FROM terms GROUP BY term_id HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        run = db.execute(
            "SELECT source_file_count, migrated_entry_count FROM migration_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if terms != EXPECTED_TERMS:
        raise SystemExit(f"Expected {EXPECTED_TERMS} terms, found {terms}")
    if source_markdown != EXPECTED_TERMS:
        raise SystemExit(f"Expected {EXPECTED_TERMS} source Markdown records, found {source_markdown}")
    if duplicates:
        raise SystemExit(f"Found {duplicates} duplicate term IDs")
    if run != (EXPECTED_TERMS, EXPECTED_TERMS):
        raise SystemExit(f"Unexpected migration provenance: {run}")
    print(f"OK: {terms} terms; SQLite integrity, provenance, and source preservation verified")


if __name__ == "__main__":
    main()
