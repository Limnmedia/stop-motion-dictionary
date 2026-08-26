#!/usr/bin/env python3
"""Migrate the LIMNMEDIA Logseq dictionary pages into SQLite.

The migration is deterministic and replaces the destination database on each
run. The original Markdown graph is never modified.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

TOOL_VERSION = "1.0"
SECTION_NAMES = {"definition", "context", "examples", "notes", "media", "related", "external links", "tags"}
WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")
URL_RE = re.compile(r"https?://[^\s)\]>]+")
TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_][A-Za-z0-9_-]*)")


def slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("[[", "").replace("]]", "")
    value = value.replace("’", "").replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "untitled"


def clean_block(value: str) -> str:
    lines = [re.sub(r"^[-*]\s+", "", line.strip()) for line in value.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def read_source(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "mac_roman"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_page(path: Path) -> dict[str, object]:
    raw = read_source(path)
    lines = raw.splitlines()
    heading = next((line[1:].strip() for line in lines if line.startswith("# ")), path.stem)
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        # Logseq exports commonly prefix child headings with a bullet.
        match = re.match(
            r"^\s*(?:-\s+)?(?:##\s+)?(Definition|Context|Examples|Notes|Media|Related|External Links|Tags)\s*:??\s*$",
            line,
            re.IGNORECASE,
        )
        if match:
            name = re.sub(r"[*_`]+", "", match.group(1)).strip().lower()
            current = name if name in SECTION_NAMES else None
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)

    related_text = clean_block("\n".join(sections.get("related", [])))
    if not related_text:
        related_text = raw
    related = []
    for label in WIKILINK_RE.findall(related_text):
        label = re.sub(r"\s+", " ", label).strip()
        if label and label not in [item[0] for item in related]:
            related.append((label, slug(label)))

    tags_text = clean_block("\n".join(sections.get("tags", [])))
    tags = []
    for label in TAG_RE.findall(tags_text):
        label = label.strip().lower()
        if label and label not in tags:
            tags.append(label)

    links = []
    for url in URL_RE.findall(raw):
        url = url.rstrip(".,;:")
        if url not in links:
            links.append(url)

    return {
        # The filename is the stable page identity. A few legacy pages have
        # duplicate headings, so using the heading alone would merge entries.
        "term_id": slug(path.stem),
        "display_name": heading,
        "definition": clean_block("\n".join(sections.get("definition", []))),
        "context": clean_block("\n".join(sections.get("context", []))),
        "examples": clean_block("\n".join(sections.get("examples", []))),
        "notes": clean_block("\n".join(sections.get("notes", []))),
        "media": clean_block("\n".join(sections.get("media", []))),
        "source_file": path.name,
        "source_markdown": raw,
        "tags": tags,
        "related": related,
        "links": links,
    }


def migrate(source: Path, destination: Path, schema: Path) -> tuple[int, int]:
    # macOS archive copies use AppleDouble names such as ._Term.md; those are
    # filesystem metadata, not dictionary entries.
    pages = sorted(
        (path for path in source.glob("*.md") if not path.name.startswith("._")),
        key=lambda path: path.name.casefold(),
    )
    entries = [parse_page(path) for path in pages]
    ids = [entry["term_id"] for entry in entries]
    duplicates = sorted({term_id for term_id in ids if ids.count(term_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate term IDs: {', '.join(duplicates)}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    connection = sqlite3.connect(destination)
    try:
        connection.executescript(schema.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        alias_map: dict[str, str | None] = {}
        for entry in entries:
            for alias in (entry["display_name"], Path(entry["source_file"]).stem):
                alias_id = slug(alias)
                if alias_id in alias_map and alias_map[alias_id] != entry["term_id"]:
                    alias_map[alias_id] = None
                else:
                    alias_map[alias_id] = entry["term_id"]
        pending_relations: list[tuple[str, str | None, str, int]] = []
        relation_seen: set[tuple[str, str]] = set()
        for entry in entries:
            connection.execute(
                """INSERT INTO terms
                   (term_id, display_name, definition, context, examples, notes,
                    media, source_file, source_markdown, source_format, status,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'logseq-markdown', 'draft', ?, ?)""",
                (entry["term_id"], entry["display_name"], entry["definition"],
                 entry["context"], entry["examples"], entry["notes"], entry["media"],
                 entry["source_file"], entry["source_markdown"], now, now),
            )
            aliases = {
                slug(alias): alias
                for alias in (entry["display_name"], Path(entry["source_file"]).stem)
            }
            for alias in aliases.values():
                connection.execute(
                    "INSERT INTO term_aliases(term_id, alias, alias_id) VALUES (?, ?, ?)",
                    (entry["term_id"], alias, slug(alias)),
                )
            for label in entry["tags"]:
                tag_id = slug(label)
                connection.execute("INSERT OR IGNORE INTO tags(tag_id, label) VALUES (?, ?)", (tag_id, label))
                connection.execute("INSERT INTO term_tags(term_id, tag_id) VALUES (?, ?)", (entry["term_id"], tag_id))
            for ordinal, (label, related_id) in enumerate(entry["related"]):
                resolved_id = alias_map.get(related_id)
                key = (entry["term_id"], resolved_id or f"label:{related_id}")
                if key not in relation_seen:
                    relation_seen.add(key)
                    pending_relations.append((entry["term_id"], resolved_id, label, ordinal))
            for url in entry["links"]:
                connection.execute("INSERT INTO external_links(term_id, url) VALUES (?, ?)", (entry["term_id"], url))
        connection.executemany(
            "INSERT INTO term_relations(term_id, related_term_id, related_label, ordinal) VALUES (?, ?, ?, ?)",
            pending_relations,
        )
        connection.execute(
            "INSERT INTO migration_runs(source_path, source_file_count, migrated_entry_count, migrated_at, tool_version) VALUES (?, ?, ?, ?, ?)",
            (str(source), len(pages), len(entries), now, TOOL_VERSION),
        )
        connection.commit()
        connection.execute("PRAGMA optimize")
        return len(pages), len(entries)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Logseq pages directory")
    parser.add_argument("destination", type=Path, help="SQLite output path")
    parser.add_argument("--schema", type=Path, default=Path(__file__).with_name("schema.sql"))
    args = parser.parse_args()
    pages, entries = migrate(args.source, args.destination, args.schema)
    print(f"Migrated {entries} entries from {pages} Markdown pages into {args.destination}")


if __name__ == "__main__":
    main()
