CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    doc_type    TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    page_count  INTEGER,
    file_size   INTEGER
);

CREATE TABLE IF NOT EXISTS page_evidence (
    id                TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(id),
    page_number       INTEGER NOT NULL,
    text              TEXT,
    extraction_method TEXT NOT NULL,
    confidence        REAL NOT NULL,
    UNIQUE(document_id, page_number)
);

CREATE TABLE IF NOT EXISTS extracted_claims (
    id                TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(id),
    page_number       INTEGER NOT NULL,
    claim_type        TEXT NOT NULL,
    entity            TEXT NOT NULL,
    parameter_name    TEXT NOT NULL,
    value_raw         TEXT NOT NULL,
    value_normalized  TEXT,
    unit              TEXT,
    condition         TEXT,
    source_text       TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    confidence        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS discrepancies (
    id            TEXT PRIMARY KEY,
    mismatch_type TEXT NOT NULL,
    severity      TEXT NOT NULL,
    confidence    REAL NOT NULL,
    summary       TEXT NOT NULL,
    explanation   TEXT,
    claim_a_id    TEXT REFERENCES extracted_claims(id),
    claim_b_id    TEXT REFERENCES extracted_claims(id),
    created_at    TEXT NOT NULL
);
