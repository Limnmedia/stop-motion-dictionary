#!/usr/bin/env python3
"""Classify recovered candidate labels without creating or deleting pages."""

from __future__ import annotations

import argparse
import csv
import difflib
import re
import sqlite3
from collections import Counter
from pathlib import Path


def key(value: str) -> str:
    value = re.sub(r"\([^)]*\)", "", value.casefold())
    value = re.sub(r"[\W_]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "candidate_id", "candidate", "classification", "confidence", "references",
        "likely_structural",
        "source_file_count", "closest_existing_term", "similarity", "rationale", "sample_locations",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def existing_terms(database: Path) -> list[str]:
    with sqlite3.connect(database) as db:
        return [row[0] for row in db.execute("SELECT display_name FROM terms ORDER BY display_name")]


def classify(row: dict[str, str], existing: list[tuple[str, str]]) -> dict[str, str]:
    label = row["candidate"].strip()
    candidate_key = key(label)
    exact_aliases = [term for term, term_key in existing if term_key == candidate_key]
    if exact_aliases:
        classification = "ALIAS"
        confidence = "high"
        closest = exact_aliases[0]
        similarity = "1.00"
        rationale = "Aggressive label normalization matches an existing page name."
    else:
        length_window = max(3, int(len(candidate_key) * 0.25))
        nearby = [
            (term, term_key)
            for term, term_key in existing
            if term_key[:1] == candidate_key[:1]
            and abs(len(term_key) - len(candidate_key)) <= length_window
        ]
        scored = sorted(
            ((difflib.SequenceMatcher(None, candidate_key, term_key).ratio(), term) for term, term_key in nearby),
            reverse=True,
        ) or [(0.0, "")]
        similarity, closest = scored[0]
        lower = label.casefold()
        if re.fullmatch(r"(term|related term|entries|add more|contents|references|index)", lower):
            classification, confidence = "NOT A TERM", "high"
            rationale = "Generic navigation or workflow label."
        elif any(token in lower for token in ("dictionary", "glossary", "workflow template", "page types overview")):
            classification, confidence = "NOT A TERM", "high"
            rationale = "Navigation, template, glossary, or overview label."
        elif similarity >= 0.93:
            classification, confidence = "MERGE/DUPLICATE", "medium"
            rationale = "Very close lexical match to an existing page; review spelling and parenthetical scope."
        elif int(row["references"]) >= 3:
            classification, confidence = "NEW TERM", "medium"
            rationale = "Repeated in the graph and not close to an existing page."
        else:
            classification, confidence = "REVIEW", "low"
            rationale = "Low-frequency unresolved label requiring editorial judgment."
        similarity = f"{similarity:.2f}"

    return {
        **row,
        "classification": classification,
        "confidence": confidence,
        "closest_existing_term": closest,
        "similarity": similarity,
        "rationale": rationale,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("candidate_tsv", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    existing = [(term, key(term)) for term in existing_terms(args.database)]
    rows = [classify(row, existing) for row in read_tsv(args.candidate_tsv)]
    rows.sort(key=lambda row: (row["classification"], -int(row["references"]), row["candidate"].casefold()))
    args.output.mkdir(parents=True, exist_ok=True)
    write_tsv(args.output / "normalized_candidate_terms.tsv", rows)
    counts = Counter(row["classification"] for row in rows)
    report = [
        "# Candidate Normalization Report",
        "",
        "This is a review queue, not an automatic page-creation plan. No database rows or Markdown pages were changed.",
        "",
        f"Candidates classified: {len(rows)}",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for classification in ("NEW TERM", "ALIAS", "MERGE/DUPLICATE", "NOT A TERM", "REVIEW"):
        report.append(f"| {classification} | {counts[classification]} |")
    report += [
        "",
        "`normalized_candidate_terms.tsv` preserves the candidate label, graph evidence, nearest existing term, similarity score, and classification rationale.",
        "",
        "Classification rules are conservative: repeated unresolved labels are provisional `NEW TERM` candidates; one-off labels remain `REVIEW`; close lexical matches are `ALIAS` or `MERGE/DUPLICATE`; structural labels are `NOT A TERM`.",
    ]
    (args.output / "candidate_normalization_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("; ".join(f"{name}={counts[name]}" for name in ("NEW TERM", "ALIAS", "MERGE/DUPLICATE", "NOT A TERM", "REVIEW")))


if __name__ == "__main__":
    main()
