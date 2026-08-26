PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS migration_runs (
    id INTEGER PRIMARY KEY,
    source_path TEXT NOT NULL,
    source_file_count INTEGER NOT NULL,
    migrated_entry_count INTEGER NOT NULL,
    migrated_at TEXT NOT NULL,
    tool_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS terms (
    term_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '',
    context TEXT NOT NULL DEFAULT '',
    examples TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    media TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL,
    source_markdown TEXT NOT NULL,
    source_format TEXT NOT NULL DEFAULT 'logseq-markdown',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id TEXT PRIMARY KEY,
    label TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS term_aliases (
    term_id TEXT NOT NULL REFERENCES terms(term_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_id TEXT NOT NULL,
    PRIMARY KEY (term_id, alias_id)
);

CREATE TABLE IF NOT EXISTS term_tags (
    term_id TEXT NOT NULL REFERENCES terms(term_id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (term_id, tag_id)
);

CREATE TABLE IF NOT EXISTS term_relations (
    term_id TEXT NOT NULL REFERENCES terms(term_id) ON DELETE CASCADE,
    related_term_id TEXT,
    related_label TEXT NOT NULL,
    relation_type TEXT NOT NULL DEFAULT 'related',
    ordinal INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (term_id, related_term_id, relation_type),
    FOREIGN KEY (related_term_id) REFERENCES terms(term_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS external_links (
    term_id TEXT NOT NULL REFERENCES terms(term_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    PRIMARY KEY (term_id, url)
);

CREATE INDEX IF NOT EXISTS idx_terms_display_name ON terms(display_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_terms_status ON terms(status);
CREATE INDEX IF NOT EXISTS idx_term_relations_related ON term_relations(related_term_id);
