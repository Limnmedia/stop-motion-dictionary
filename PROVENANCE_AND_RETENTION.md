# Dictionary Provenance and Retention

## Purpose

This repository preserves the usable, validated LIMNMEDIA Stop-Motion Dictionary. It is not intended to be a complete backup of every authoring environment, export, or workstation artifact used to create it.

## What Git Tracks

Git tracks the material needed to understand, validate, and develop the committed dictionary artifact:

- the canonical SQLite dictionary database
- migration, normalization, discovery, and validation scripts
- database schema
- reviewed candidate-term reports
- repository documentation and automation

The current database contains one migrated record per preserved Logseq page. Each term retains its original Markdown and source filename, alongside normalized fields, tags, internal relations, and external links.

## What Remains Outside This Repository

The original Logseq graph is a protected source archive. Its pages, journals, Logseq configuration, assets, and point-in-time exports are not duplicated here by default.

The Logseq JSON export is likewise an archival snapshot, not a second canonical dictionary artifact. Keep it with the protected source archive or another approved offline backup unless there is a specific recovery or interoperability reason to version it here.

This separation is intentional. Git is not the only backup system, and it should not become an unreviewed copy of the entire historical workstation.

## Source of Truth by Role

| Role | Artifact |
| --- | --- |
| Historical authoring source | Preserved Logseq graph |
| Recovery snapshot | Logseq JSON export and offline backups |
| Canonical repository delivery artifact | `limn_stop_motion_dictionary.sqlite` |
| Reproducibility tools | Migration and validation scripts in this repository |
| Editorial follow-up | Reviewed candidate-term reports and future issue/PR decisions |

The SQLite database is the canonical artifact delivered and validated by this repository. It does not replace the historical Logseq archive as evidence of how the corpus was authored.

## Rebuild and Recovery

Rebuilding the database requires an approved copy of the preserved Logseq source graph. The migration is read-only with respect to that source.

Before accepting a rebuilt database:

1. Confirm the intended source archive and snapshot date.
2. Run the migration into a new database file.
3. Run `validate_database.py`.
4. Compare entry counts, source filenames, and meaningful validation results with the committed artifact.
5. Review the database diff and commit scripts, reports, and database together only when the change is intentional.

Do not silently replace the committed database from an unknown export, an incomplete graph, or a newly discovered workstation copy.

## Git Intake Rules

Do not commit these by default:

- complete workstation backups
- raw Logseq configuration or local application state
- temporary exports, caches, SQLite sidecars, or Python bytecode
- unreviewed personal, client, financial, legal, credential, or unpublished material
- large media unless it is explicitly reviewed as an owned, necessary repository asset

Before adding any recovered source artifact, decide whether it is needed for reproducibility, editorial work, or recovery. If it is not, retain it in the protected archive rather than Git.

## Current Baseline

The present repository baseline was migrated from a preserved Logseq graph containing 1,077 Markdown pages. Its JSON export is a matching point-in-time snapshot of the same graph, including journal and asset records. The archive should remain preserved even though its full contents are not committed here.
