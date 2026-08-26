#!/usr/bin/env python3
"""Discover candidate dictionary terms from a preserved Logseq graph."""

from __future__ import annotations

import argparse
import csv
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
SOURCE_HINT_RE = re.compile(
    r"(?i)(candidate|backlog|to.?add|unfinished|missing|index|glossar|dictionar|term)"
)
STRUCTURAL_RE = re.compile(
    r"(?i)^(dictionary(?:\s+[—-]\s+[a-z])?|contents|references|index|workflow|template|overview|entries|add more)$"
)


def normalize(value: str) -> str:
    value = urllib.parse.unquote(value).strip().replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    # Treat legacy filename separators such as ___ and punctuation in links
    # as equivalent word boundaries.
    value = re.sub(r"[\W_]+", "-", value, flags=re.UNICODE).strip("-")
    return value.casefold()


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "mac_roman"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def discover(source: Path, output: Path) -> None:
    files = sorted(
        (path for path in source.rglob("*.md") if not path.name.startswith("._")),
        key=lambda path: str(path).casefold(),
    )
    page_dir = source / "pages"
    page_files = [path for path in files if page_dir in path.parents]
    existing: dict[str, str] = {}
    for path in page_files:
        existing.setdefault(normalize(path.stem), path.name)
        for line in read_text(path).splitlines():
            if line.startswith("# "):
                existing.setdefault(normalize(line[2:]), path.name)
                break

    candidates: dict[str, dict[str, object]] = {}
    source_hits: list[dict[str, str]] = []
    research_sources: list[dict[str, str]] = []
    for path in files:
        text = read_text(path)
        relative = str(path.relative_to(source)).replace("\\", "/")
        if SOURCE_HINT_RE.search(path.name):
            source_hits.append({
                "source_file": relative,
                "reason": "filename matches candidate/index/listing vocabulary",
                "line_count": str(len(text.splitlines())),
            })
            for label, url in MARKDOWN_LINK_RE.findall(text):
                research_sources.append({
                    "source_file": relative,
                    "label": re.sub(r"\s+", " ", label).strip(),
                    "url": url,
                })
        for line_number, line in enumerate(text.splitlines(), start=1):
            for raw_label in WIKILINK_RE.findall(line):
                label = re.sub(r"\s+", " ", raw_label).strip()
                key = normalize(label)
                if not label or key in existing:
                    continue
                item = candidates.setdefault(
                    key,
                    {
                        "candidate_id": key,
                        "candidate": label,
                        "references": 0,
                        "source_files": set(),
                        "locations": [],
                    },
                )
                item["references"] = int(item["references"]) + 1
                item["source_files"].add(relative)
                locations = item["locations"]
                if len(locations) < 5:
                    locations.append(f"{relative}:{line_number}")

    candidate_rows = []
    for item in candidates.values():
        label = str(item["candidate"])
        structural = "yes" if STRUCTURAL_RE.search(label) else "no"
        candidate_rows.append({
            "candidate_id": str(item["candidate_id"]),
            "candidate": label,
            "references": str(item["references"]),
            "source_file_count": str(len(item["source_files"])),
            "likely_structural": structural,
            "sample_locations": "; ".join(item["locations"]),
        })
    candidate_rows.sort(key=lambda row: (-int(row["references"]), row["candidate"].casefold()))
    source_hits.sort(key=lambda row: row["source_file"].casefold())

    output.mkdir(parents=True, exist_ok=True)
    write_tsv(output / "candidate_terms.tsv", candidate_rows, list(candidate_rows[0]) if candidate_rows else [
        "candidate_id", "candidate", "references", "source_file_count", "likely_structural", "sample_locations"
    ])
    write_tsv(output / "candidate_source_pages.tsv", source_hits, ["source_file", "reason", "line_count"])
    write_tsv(output / "research_source_links.tsv", research_sources, ["source_file", "label", "url"])
    unresolved = len(candidate_rows)
    references = sum(int(row["references"]) for row in candidate_rows)
    structural = sum(row["likely_structural"] == "yes" for row in candidate_rows)
    report = [
        "# Candidate-Term Discovery Report",
        "",
        f"Source: `{source}`",
        f"Scanned Markdown files: {len(files)} ({len(page_files)} pages and {len(files) - len(page_files)} other graph files)",
        f"Existing page identities: {len(existing)}",
        f"Unique unresolved wikilink candidates: {unresolved}",
        f"Total unresolved wikilink references: {references}",
        f"Likely structural/navigation candidates: {structural}",
        "",
        "`candidate_terms.tsv` is the deduplicated candidate pool. Candidates are ranked by reference count and retain sample source locations.",
        "`candidate_source_pages.tsv` identifies graph files whose names suggest indexes, glossaries, backlogs, or term lists.",
        "`research_source_links.tsv` extracts the external research links from those source-list pages for later term harvesting.",
        "",
        "## Interpretation",
        "",
        "Unresolved wikilinks are leads, not automatically valid dictionary terms. Review structural/navigation labels and merge spelling, punctuation, and alias variants before creating pages.",
    ]
    (output / "candidate_discovery_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Scanned {len(files)} files; found {unresolved} unique unresolved wikilink candidates ({references} references).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="old-logseq graph directory")
    parser.add_argument("output", type=Path, help="report output directory")
    args = parser.parse_args()
    discover(args.source, args.output)


if __name__ == "__main__":
    main()
