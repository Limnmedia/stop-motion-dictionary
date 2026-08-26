# LIMNMEDIA Stop-Motion Dictionary

This directory contains the canonical local SQLite database generated from the preserved Logseq page export. The source graph is read-only and is not modified by the migration.

## Build or rebuild

```powershell
python .\migrate_logseq.py `
  D:\LIMNMEDIA_LLC\04-LIMN-EDU\LIMN-WIKI\dictionary\old-logseq\pages `
  .\limn_stop_motion_dictionary.sqlite
```

The migration stores the original Markdown in `terms.source_markdown` and keeps the source filename in `terms.source_file`, so no entry content is lost. It also normalizes tags, internal related-term links, and external URLs into separate tables.

The current migrated database contains 1,077 entries. The 36 records without a recognized Definition section are retained as-is for later cleanup; most are index, reference, or template pages. Only `Japanese animation (anime)` is an actual dictionary term with no substantive content yet.

Run `python .\validate_database.py` to verify the committed database.

## Candidate-term discovery

The preserved Logseq graph was scanned for unresolved `[[wikilinks]]`, index/list pages, and research-source pages. The resulting auditable candidate pool is in [`reports/candidate-pool/`](reports/candidate-pool/): 1,324 unique unresolved labels across 3,419 references, plus the 14 external resources from the `Film & Animation Dictionaries & Glossaries` source-list page.

Rebuild the report with:

```powershell
python .\discover_candidates.py `
  D:\LIMNMEDIA_LLC\04-LIMN-EDU\LIMN-WIKI\dictionary\old-logseq `
  .\reports\candidate-pool
```

## Tables

- `terms`: one row per Logseq page, including the original Markdown.
- `tags` and `term_tags`: normalized hashtags.
- `term_relations`: resolved `[[Term]]` links whose target exists in the corpus.
- `external_links`: normalized HTTP(S) links.
- `migration_runs`: provenance and repeatable migration metadata.
