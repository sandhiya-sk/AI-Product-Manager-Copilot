# AI Product Manager Copilot — PostgreSQL Database Schema (Modules 1–3)

> This file contains the exact, complete PostgreSQL schema for all tables required through Module 3.
> All tables use `gen_random_uuid()` (requires `pgcrypto` extension) for UUID generation.
> All timestamps are stored in UTC using `TIMESTAMPTZ`.

---

## Extension Setup

```sql
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable full-text search (optional, useful for Module 4+)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## Table 1: `users`

Stores both Product Managers and Customers. Used for authentication and role-based access control.

```sql
CREATE TABLE users (
    -- Primary Key
    user_id             UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    email               VARCHAR(255)    NOT NULL UNIQUE,
    password_hash       VARCHAR(255)    NOT NULL,
    full_name           VARCHAR(255),

    -- Role-Based Access Control
    role                VARCHAR(50)     NOT NULL
                            CHECK (role IN ('product_manager', 'customer')),

    -- Project Association (optional, can be assigned later)
    project_id          UUID,

    -- Account Status
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,

    -- Audit Timestamps
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_users_email        ON users (email);
CREATE INDEX idx_users_role         ON users (role);
CREATE INDEX idx_users_project_id   ON users (project_id);

-- Comments
COMMENT ON TABLE  users                 IS 'Stores product manager and customer accounts';
COMMENT ON COLUMN users.user_id         IS 'Unique identifier for the user (UUID)';
COMMENT ON COLUMN users.email           IS 'Unique login email address';
COMMENT ON COLUMN users.password_hash   IS 'bcrypt-hashed password';
COMMENT ON COLUMN users.role            IS 'User role: product_manager or customer';
COMMENT ON COLUMN users.project_id      IS 'Default project association for this user';
COMMENT ON COLUMN users.is_active       IS 'Soft delete flag; FALSE = account disabled';
```

---

## Table 2: `raw_feedback`

Stores all feedback records as they arrive — from CSV uploads (Product Manager) and text form submissions (PM or Customer). This is the source-of-truth raw input table. Records here are waiting to be processed by Module 3.

```sql
CREATE TABLE raw_feedback (
    -- =========================================================
    -- PRIMARY KEY
    -- =========================================================
    feedback_id             UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- =========================================================
    -- SOURCE & SUBMITTER INFORMATION
    -- =========================================================
    source                  VARCHAR(50)     NOT NULL
                                CHECK (source IN ('csv_upload', 'text_form')),
    submitted_by_role       VARCHAR(50)     NOT NULL
                                CHECK (submitted_by_role IN ('product_manager', 'customer')),
    user_id                 UUID            NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    project_id              UUID            NOT NULL,

    -- =========================================================
    -- CUSTOMER INFORMATION (optional, relevant for CSV rows)
    -- =========================================================
    customer_name           VARCHAR(255),
    customer_email          VARCHAR(255),

    -- =========================================================
    -- FEEDBACK CONTENT (core fields)
    -- =========================================================
    subject                 TEXT            NOT NULL,
    description             TEXT            NOT NULL,

    -- =========================================================
    -- STRUCTURED METADATA FIELDS
    -- =========================================================
    priority                VARCHAR(50)     NOT NULL DEFAULT 'Medium'
                                CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    category                VARCHAR(100)    NOT NULL DEFAULT 'General'
                                CHECK (category IN (
                                    'Bug',
                                    'Feature Request',
                                    'Improvement',
                                    'Complaint',
                                    'General'
                                )),
    product_name            VARCHAR(255),
    product_version         VARCHAR(100),
    submission_date         DATE,
    tags                    TEXT[],                         -- Array of tag strings
    sentiment_self_reported VARCHAR(50)
                                CHECK (sentiment_self_reported IN (
                                    'Positive', 'Negative', 'Neutral'
                                ) OR sentiment_self_reported IS NULL),
    language                VARCHAR(10)     NOT NULL DEFAULT 'en',

    -- =========================================================
    -- INGESTION AUDIT METADATA
    -- =========================================================
    upload_timestamp        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    raw_metadata            JSONB           NOT NULL DEFAULT '{}',
    -- raw_metadata JSONB structure:
    -- {
    --   "original_filename": "feedback_q3.csv",
    --   "file_row_number": 42,
    --   "ip_address": "192.168.1.10",
    --   "user_agent": "Mozilla/5.0 ...",
    --   "batch_id": "uuid-string"
    -- }

    -- =========================================================
    -- CANONICAL JSON SNAPSHOT
    -- =========================================================
    canonical_json          JSONB           NOT NULL DEFAULT '{}',
    -- Stores the full canonical JSON dict that was built during ingestion
    -- This is the complete normalized representation of the record at time of ingest

    -- =========================================================
    -- DEDUPLICATION FIELDS (populated by Module 3)
    -- =========================================================
    weight                  INTEGER         NOT NULL DEFAULT 1
                                CHECK (weight >= 1),
    -- weight = count of semantically duplicate records merged into this canonical record
    -- Initial value: 1 (just itself)
    -- Updated by Module 3 deduplication engine

    duplicate_group_id      UUID,
    -- NULL until Module 3 runs
    -- After deduplication: all records in the same semantic group share this UUID
    -- The canonical (oldest) record in the group is the one kept in processed_feedback

    -- =========================================================
    -- PROCESSING STATUS (lifecycle tracking)
    -- =========================================================
    processing_status       VARCHAR(50)     NOT NULL DEFAULT 'pending'
                                CHECK (processing_status IN (
                                    'pending',      -- Not yet processed
                                    'processing',   -- Currently being processed
                                    'processed',    -- Successfully processed, moved to processed_feedback
                                    'duplicate',    -- Identified as duplicate, weight added to canonical
                                    'failed'        -- Processing failed (see processing_error)
                                )),
    processing_error        TEXT,
    -- NULL if no error; populated with error message if processing_status = 'failed'

    processed_at            TIMESTAMPTZ,
    -- Populated when processing_status transitions to 'processed' or 'duplicate'

    -- =========================================================
    -- AUDIT TIMESTAMPS
    -- =========================================================
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- =========================================================
-- INDEXES FOR raw_feedback
-- =========================================================

-- For filtering by processing status (Module 3 fetches pending records)
CREATE INDEX idx_raw_feedback_processing_status
    ON raw_feedback (processing_status);

-- For filtering by project
CREATE INDEX idx_raw_feedback_project_id
    ON raw_feedback (project_id);

-- For filtering by user
CREATE INDEX idx_raw_feedback_user_id
    ON raw_feedback (user_id);

-- For sorting by upload time (Module 3 uses this for canonical selection)
CREATE INDEX idx_raw_feedback_upload_timestamp
    ON raw_feedback (upload_timestamp ASC);

-- For grouping duplicates
CREATE INDEX idx_raw_feedback_duplicate_group_id
    ON raw_feedback (duplicate_group_id)
    WHERE duplicate_group_id IS NOT NULL;

-- For filtering by source type
CREATE INDEX idx_raw_feedback_source
    ON raw_feedback (source);

-- For filtering by category and priority (used in dashboards)
CREATE INDEX idx_raw_feedback_category_priority
    ON raw_feedback (category, priority);

-- For querying batch uploads via JSONB
CREATE INDEX idx_raw_feedback_batch_id
    ON raw_feedback USING GIN ((raw_metadata -> 'batch_id'));

-- For full-text search on subject and description (future use)
CREATE INDEX idx_raw_feedback_subject_gin
    ON raw_feedback USING GIN (to_tsvector('english', subject));

CREATE INDEX idx_raw_feedback_description_gin
    ON raw_feedback USING GIN (to_tsvector('english', description));

-- =========================================================
-- COMMENTS FOR raw_feedback
-- =========================================================
COMMENT ON TABLE  raw_feedback                      IS 'Raw ingested feedback from CSV uploads and text forms. Source of truth for Module 3 processing.';
COMMENT ON COLUMN raw_feedback.feedback_id          IS 'Unique UUID per feedback record';
COMMENT ON COLUMN raw_feedback.source               IS 'csv_upload = from PM CSV file; text_form = manual form submission';
COMMENT ON COLUMN raw_feedback.submitted_by_role    IS 'Role of the user who submitted this feedback';
COMMENT ON COLUMN raw_feedback.user_id              IS 'FK to users table; who uploaded/submitted this';
COMMENT ON COLUMN raw_feedback.project_id           IS 'UUID of the product/project this feedback belongs to';
COMMENT ON COLUMN raw_feedback.customer_name        IS 'Name of customer (from CSV) or null for form submissions';
COMMENT ON COLUMN raw_feedback.customer_email       IS 'Email of customer (from CSV) or null';
COMMENT ON COLUMN raw_feedback.subject              IS 'Short title or subject line of the feedback';
COMMENT ON COLUMN raw_feedback.description          IS 'Full text body of the feedback';
COMMENT ON COLUMN raw_feedback.priority             IS 'Normalized priority: Low / Medium / High / Critical';
COMMENT ON COLUMN raw_feedback.category             IS 'Normalized category enum';
COMMENT ON COLUMN raw_feedback.product_name         IS 'Product being reviewed (optional)';
COMMENT ON COLUMN raw_feedback.product_version      IS 'Product version (optional)';
COMMENT ON COLUMN raw_feedback.submission_date      IS 'Original date of feedback (from CSV), if available';
COMMENT ON COLUMN raw_feedback.tags                 IS 'Array of tag strings extracted from CSV or form input';
COMMENT ON COLUMN raw_feedback.sentiment_self_reported IS 'Self-reported sentiment by the submitter (optional)';
COMMENT ON COLUMN raw_feedback.language             IS 'Detected or assumed language code (default: en)';
COMMENT ON COLUMN raw_feedback.upload_timestamp     IS 'UTC timestamp when record was inserted into this table';
COMMENT ON COLUMN raw_feedback.raw_metadata         IS 'JSONB blob: original filename, row number, IP, batch_id, user agent';
COMMENT ON COLUMN raw_feedback.canonical_json       IS 'Full canonical JSON snapshot built at ingestion time';
COMMENT ON COLUMN raw_feedback.weight               IS 'Semantic frequency weight. Starts at 1, incremented by Module 3 for each duplicate found';
COMMENT ON COLUMN raw_feedback.duplicate_group_id   IS 'UUID shared by all semantically similar records in the same group. NULL until Module 3 runs.';
COMMENT ON COLUMN raw_feedback.processing_status    IS 'Lifecycle: pending → processing → processed | duplicate | failed';
COMMENT ON COLUMN raw_feedback.processing_error     IS 'Error message if processing_status = failed';
COMMENT ON COLUMN raw_feedback.processed_at         IS 'Timestamp when Module 3 finished processing this record';
```

---

## Table 3: `processed_feedback`

Stores the fully cleaned, standardized, tokenized, and lemmatized version of each canonical (non-duplicate) feedback record. One row per canonical record. Ready for Module 4 (classification and theme extraction).

```sql
CREATE TABLE processed_feedback (
    -- =========================================================
    -- PRIMARY KEY
    -- =========================================================
    processed_id                UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- =========================================================
    -- LINK BACK TO RAW FEEDBACK
    -- =========================================================
    raw_feedback_id             UUID            NOT NULL
                                    REFERENCES raw_feedback(feedback_id) ON DELETE CASCADE,
    -- The canonical raw_feedback record that this processed record was derived from

    -- =========================================================
    -- SOURCE & IDENTITY FIELDS (inherited from raw_feedback)
    -- =========================================================
    source                      VARCHAR(50)     NOT NULL
                                    CHECK (source IN ('csv_upload', 'text_form')),
    submitted_by_role           VARCHAR(50)     NOT NULL
                                    CHECK (submitted_by_role IN ('product_manager', 'customer')),
    user_id                     UUID            NOT NULL,
    project_id                  UUID            NOT NULL,

    -- =========================================================
    -- ORIGINAL & CLEANED TEXT
    -- =========================================================
    original_subject            TEXT            NOT NULL,
    -- The subject as stored in raw_feedback (unchanged)

    original_description        TEXT            NOT NULL,
    -- The description as stored in raw_feedback (unchanged)

    clean_text                  TEXT            NOT NULL,
    -- After: remove HTML, URLs, emojis, extra spaces, special chars

    standardized_text           TEXT            NOT NULL,
    -- After: lowercase, normalized punctuation, date normalization

    -- =========================================================
    -- NLP OUTPUT FIELDS
    -- =========================================================
    tokens                      TEXT[]          NOT NULL DEFAULT '{}',
    -- NLTK word_tokenize output with stop words removed
    -- Stored as PostgreSQL TEXT array

    lemmas                      TEXT[]          NOT NULL DEFAULT '{}',
    -- spaCy lemmatized tokens
    -- Stored as PostgreSQL TEXT array

    -- =========================================================
    -- STRUCTURED METADATA (inherited & normalized)
    -- =========================================================
    priority                    VARCHAR(50)     NOT NULL DEFAULT 'Medium'
                                    CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    category                    VARCHAR(100)    NOT NULL DEFAULT 'General'
                                    CHECK (category IN (
                                        'Bug',
                                        'Feature Request',
                                        'Improvement',
                                        'Complaint',
                                        'General'
                                    )),
    product_name                VARCHAR(255),
    product_version             VARCHAR(100),
    tags                        TEXT[],
    sentiment_self_reported     VARCHAR(50)
                                    CHECK (sentiment_self_reported IN (
                                        'Positive', 'Negative', 'Neutral'
                                    ) OR sentiment_self_reported IS NULL),
    language                    VARCHAR(10)     NOT NULL DEFAULT 'en',
    submission_date             DATE,

    -- =========================================================
    -- DEDUPLICATION FIELDS (from Module 3)
    -- =========================================================
    weight                      INTEGER         NOT NULL DEFAULT 1
                                    CHECK (weight >= 1),
    -- Final aggregated weight after duplicate merging
    -- Equals the number of semantically similar records collapsed into this one

    duplicate_group_id          UUID            NOT NULL,
    -- UUID shared by all records in the same semantic group
    -- Always populated in processed_feedback (unlike raw_feedback where it may be NULL initially)

    -- =========================================================
    -- TEXT STATISTICS (computed metadata)
    -- =========================================================
    word_count                  INTEGER         NOT NULL DEFAULT 0,
    -- len(clean_text.split())

    char_count                  INTEGER         NOT NULL DEFAULT 0,
    -- len(clean_text)

    token_count                 INTEGER         NOT NULL DEFAULT 0,
    -- len(tokens)

    lemma_count                 INTEGER         NOT NULL DEFAULT 0,
    -- len(lemmas)

    -- =========================================================
    -- PROCESSING METADATA
    -- =========================================================
    processing_metadata         JSONB           NOT NULL DEFAULT '{}',
    -- Structure:
    -- {
    --   "nlp_model_version": "spacy-en_core_web_sm-3",
    --   "embedding_model": "all-MiniLM-L6-v2",
    --   "similarity_threshold_used": 0.85,
    --   "pipeline_version": "1.0.0",
    --   "processing_duration_ms": 142
    -- }

    processing_status           VARCHAR(50)     NOT NULL DEFAULT 'processed'
                                    CHECK (processing_status IN (
                                        'processed',    -- Successfully processed
                                        'failed',       -- Processing failed
                                        'reprocessing'  -- Being reprocessed (future use)
                                    )),
    processing_error            TEXT,
    -- NULL normally; populated if processing_status = 'failed'

    -- =========================================================
    -- SEARCH & INDEXING METADATA
    -- =========================================================
    search_vector               TSVECTOR,
    -- Pre-computed PostgreSQL full-text search vector from clean_text
    -- Updated via trigger or explicitly on insert

    -- =========================================================
    -- TIMESTAMPS
    -- =========================================================
    processing_timestamp        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    -- When Module 3 finished processing this record

    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- =========================================================
    -- MODULE 4 READINESS FLAG
    -- =========================================================
    ready_for_classification    BOOLEAN         NOT NULL DEFAULT TRUE,
    -- Set to TRUE when all NLP fields are populated
    -- Module 4 will query WHERE ready_for_classification = TRUE
    -- AND classified_at IS NULL

    classified_at               TIMESTAMPTZ
    -- Populated by Module 4 when classification is complete
    -- NULL = not yet classified by Module 4
);

-- =========================================================
-- TRIGGER: Auto-update search_vector from clean_text
-- =========================================================
CREATE OR REPLACE FUNCTION update_processed_feedback_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.original_subject, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.clean_text, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_processed_feedback_search_vector
    BEFORE INSERT OR UPDATE OF original_subject, clean_text
    ON processed_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_processed_feedback_search_vector();

-- =========================================================
-- TRIGGER: Auto-update updated_at on row modification
-- =========================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_processed_feedback_updated_at
    BEFORE UPDATE ON processed_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_raw_feedback_updated_at
    BEFORE UPDATE ON raw_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================================================
-- INDEXES FOR processed_feedback
-- =========================================================

-- For Module 4: fetch all unclassified processed records
CREATE INDEX idx_processed_feedback_ready_for_classification
    ON processed_feedback (ready_for_classification, classified_at)
    WHERE ready_for_classification = TRUE AND classified_at IS NULL;

-- For filtering by project
CREATE INDEX idx_processed_feedback_project_id
    ON processed_feedback (project_id);

-- For deduplication group lookups
CREATE INDEX idx_processed_feedback_duplicate_group_id
    ON processed_feedback (duplicate_group_id);

-- For sorting by weight (high-demand features float to top)
CREATE INDEX idx_processed_feedback_weight
    ON processed_feedback (weight DESC);

-- For category and priority filtering
CREATE INDEX idx_processed_feedback_category
    ON processed_feedback (category);

CREATE INDEX idx_processed_feedback_priority
    ON processed_feedback (priority);

-- For linking back to raw record
CREATE INDEX idx_processed_feedback_raw_id
    ON processed_feedback (raw_feedback_id);

-- For full-text search
CREATE INDEX idx_processed_feedback_search_vector
    ON processed_feedback USING GIN (search_vector);

-- For processing status filtering
CREATE INDEX idx_processed_feedback_status
    ON processed_feedback (processing_status);

-- For timestamp-based sorting and reporting
CREATE INDEX idx_processed_feedback_processing_timestamp
    ON processed_feedback (processing_timestamp DESC);

-- =========================================================
-- COMMENTS FOR processed_feedback
-- =========================================================
COMMENT ON TABLE  processed_feedback                            IS 'NLP-processed feedback records. One row per canonical (non-duplicate) raw_feedback. Ready for Module 4 classification.';
COMMENT ON COLUMN processed_feedback.processed_id              IS 'Unique UUID for this processed record';
COMMENT ON COLUMN processed_feedback.raw_feedback_id           IS 'FK to the canonical raw_feedback record this was derived from';
COMMENT ON COLUMN processed_feedback.original_subject          IS 'Unmodified subject from raw_feedback';
COMMENT ON COLUMN processed_feedback.original_description      IS 'Unmodified description from raw_feedback';
COMMENT ON COLUMN processed_feedback.clean_text                IS 'Text after HTML/URL/emoji/whitespace removal';
COMMENT ON COLUMN processed_feedback.standardized_text         IS 'Text after lowercase conversion and normalization';
COMMENT ON COLUMN processed_feedback.tokens                    IS 'NLTK tokenized word list with stop words removed';
COMMENT ON COLUMN processed_feedback.lemmas                    IS 'spaCy lemmatized token list';
COMMENT ON COLUMN processed_feedback.weight                    IS 'Number of semantically duplicate records merged into this canonical record';
COMMENT ON COLUMN processed_feedback.duplicate_group_id        IS 'UUID of the semantic duplicate group (shared across all duplicates)';
COMMENT ON COLUMN processed_feedback.word_count                IS 'Word count of clean_text';
COMMENT ON COLUMN processed_feedback.char_count                IS 'Character count of clean_text';
COMMENT ON COLUMN processed_feedback.token_count               IS 'Number of tokens after tokenization';
COMMENT ON COLUMN processed_feedback.lemma_count               IS 'Number of lemmas after lemmatization';
COMMENT ON COLUMN processed_feedback.processing_metadata       IS 'JSONB: NLP model versions, pipeline version, processing duration';
COMMENT ON COLUMN processed_feedback.search_vector             IS 'Pre-computed tsvector for PostgreSQL full-text search';
COMMENT ON COLUMN processed_feedback.processing_timestamp      IS 'UTC timestamp when Module 3 inserted this record';
COMMENT ON COLUMN processed_feedback.ready_for_classification  IS 'TRUE when ready for Module 4 to classify';
COMMENT ON COLUMN processed_feedback.classified_at             IS 'Populated by Module 4; NULL = not yet classified';
```

---

## Full Schema Summary Table

| Table | Rows at Module 3 End | Key Purpose |
|-------|---------------------|-------------|
| `users` | N users (PMs + Customers) | Authentication, RBAC |
| `raw_feedback` | All ingested records | Source-of-truth raw storage |
| `processed_feedback` | Canonical records only | NLP output, ready for Module 4 |

---

## Entity Relationship Diagram

```
┌─────────────────────────────────┐
│            users                │
│─────────────────────────────────│
│ user_id (PK)                    │
│ email (UNIQUE)                  │
│ password_hash                   │
│ full_name                       │
│ role                            │
│ project_id                      │
│ is_active                       │
│ created_at                      │
└──────────────┬──────────────────┘
               │ 1
               │
               │ M
┌──────────────▼──────────────────┐
│          raw_feedback           │
│─────────────────────────────────│
│ feedback_id (PK)                │
│ source                          │
│ submitted_by_role               │
│ user_id (FK → users)            │
│ project_id                      │
│ customer_name                   │
│ customer_email                  │
│ subject                         │
│ description                     │
│ priority                        │
│ category                        │
│ product_name                    │
│ product_version                 │
│ submission_date                 │
│ tags[]                          │
│ sentiment_self_reported         │
│ language                        │
│ upload_timestamp                │
│ raw_metadata (JSONB)            │
│ canonical_json (JSONB)          │
│ weight                          │
│ duplicate_group_id              │
│ processing_status               │
│ processing_error                │
│ processed_at                    │
│ created_at                      │
│ updated_at                      │
└──────────────┬──────────────────┘
               │ 1
               │ (canonical records only)
               │ 1
┌──────────────▼──────────────────┐
│       processed_feedback        │
│─────────────────────────────────│
│ processed_id (PK)               │
│ raw_feedback_id (FK → raw)      │
│ source                          │
│ submitted_by_role               │
│ user_id                         │
│ project_id                      │
│ original_subject                │
│ original_description            │
│ clean_text                      │
│ standardized_text               │
│ tokens[]                        │
│ lemmas[]                        │
│ priority                        │
│ category                        │
│ product_name                    │
│ product_version                 │
│ tags[]                          │
│ sentiment_self_reported         │
│ language                        │
│ submission_date                 │
│ weight                          │
│ duplicate_group_id              │
│ word_count                      │
│ char_count                      │
│ token_count                     │
│ lemma_count                     │
│ processing_metadata (JSONB)     │
│ processing_status               │
│ processing_error                │
│ search_vector (TSVECTOR)        │
│ processing_timestamp            │
│ ready_for_classification        │
│ classified_at                   │
│ created_at                      │
│ updated_at                      │
└─────────────────────────────────┘
```

---

## Column Count Summary

| Table | Column Count |
|-------|-------------|
| `users` | 8 columns |
| `raw_feedback` | 24 columns |
| `processed_feedback` | 32 columns |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `TEXT[]` for tokens and lemmas | Native PostgreSQL array type, queryable with `@>` (contains) operator |
| `JSONB` for `raw_metadata` and `processing_metadata` | Flexible schema for variable metadata; GIN-indexable |
| `JSONB` for `canonical_json` | Full snapshot of the record at ingestion; enables replay without data loss |
| `TSVECTOR` for `search_vector` | Enables fast full-text search in Module 4+ without external search engine |
| `weight INTEGER` | Simple integer counter for duplicate frequency; incremented by deduplication engine |
| `duplicate_group_id UUID` | Allows grouping all semantically similar records across both tables |
| `processing_status` enum | Lifecycle states: `pending → processing → processed / duplicate / failed` |
| `ready_for_classification BOOLEAN` | Clean handoff signal between Module 3 and Module 4 |
| `classified_at TIMESTAMPTZ` | Module 4 sets this when done; NULL = not yet classified |
| UTC timestamps (`TIMESTAMPTZ`) | All times in UTC, display conversion done at application layer |
| Soft deletes via `is_active` | Users are never hard-deleted; audit trail preserved |

---

## Full Migration File (for `backend/database/migrations/init_schema.sql`)

```sql
-- ============================================================
-- AI Product Manager Copilot — Initial Schema Migration
-- Version: 1.0.0
-- Modules: 1, 2, 3
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id         UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255)    NOT NULL UNIQUE,
    password_hash   VARCHAR(255)    NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50)     NOT NULL CHECK (role IN ('product_manager', 'customer')),
    project_id      UUID,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email        ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role         ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_project_id   ON users (project_id);

-- ============================================================
-- TABLE: raw_feedback
-- ============================================================
CREATE TABLE IF NOT EXISTS raw_feedback (
    feedback_id             UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    source                  VARCHAR(50)     NOT NULL CHECK (source IN ('csv_upload', 'text_form')),
    submitted_by_role       VARCHAR(50)     NOT NULL CHECK (submitted_by_role IN ('product_manager', 'customer')),
    user_id                 UUID            NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    project_id              UUID            NOT NULL,
    customer_name           VARCHAR(255),
    customer_email          VARCHAR(255),
    subject                 TEXT            NOT NULL,
    description             TEXT            NOT NULL,
    priority                VARCHAR(50)     NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    category                VARCHAR(100)    NOT NULL DEFAULT 'General' CHECK (category IN ('Bug', 'Feature Request', 'Improvement', 'Complaint', 'General')),
    product_name            VARCHAR(255),
    product_version         VARCHAR(100),
    submission_date         DATE,
    tags                    TEXT[],
    sentiment_self_reported VARCHAR(50) CHECK (sentiment_self_reported IN ('Positive', 'Negative', 'Neutral') OR sentiment_self_reported IS NULL),
    language                VARCHAR(10)     NOT NULL DEFAULT 'en',
    upload_timestamp        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    raw_metadata            JSONB           NOT NULL DEFAULT '{}',
    canonical_json          JSONB           NOT NULL DEFAULT '{}',
    weight                  INTEGER         NOT NULL DEFAULT 1 CHECK (weight >= 1),
    duplicate_group_id      UUID,
    processing_status       VARCHAR(50)     NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'processed', 'duplicate', 'failed')),
    processing_error        TEXT,
    processed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_feedback_processing_status   ON raw_feedback (processing_status);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_project_id          ON raw_feedback (project_id);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_user_id             ON raw_feedback (user_id);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_upload_timestamp    ON raw_feedback (upload_timestamp ASC);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_duplicate_group_id  ON raw_feedback (duplicate_group_id) WHERE duplicate_group_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_raw_feedback_source              ON raw_feedback (source);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_category_priority   ON raw_feedback (category, priority);
CREATE INDEX IF NOT EXISTS idx_raw_feedback_batch_id            ON raw_feedback USING GIN ((raw_metadata -> 'batch_id'));
CREATE INDEX IF NOT EXISTS idx_raw_feedback_subject_gin         ON raw_feedback USING GIN (to_tsvector('english', subject));

-- ============================================================
-- TABLE: processed_feedback
-- ============================================================
CREATE TABLE IF NOT EXISTS processed_feedback (
    processed_id                UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_feedback_id             UUID            NOT NULL REFERENCES raw_feedback(feedback_id) ON DELETE CASCADE,
    source                      VARCHAR(50)     NOT NULL CHECK (source IN ('csv_upload', 'text_form')),
    submitted_by_role           VARCHAR(50)     NOT NULL CHECK (submitted_by_role IN ('product_manager', 'customer')),
    user_id                     UUID            NOT NULL,
    project_id                  UUID            NOT NULL,
    original_subject            TEXT            NOT NULL,
    original_description        TEXT            NOT NULL,
    clean_text                  TEXT            NOT NULL,
    standardized_text           TEXT            NOT NULL,
    tokens                      TEXT[]          NOT NULL DEFAULT '{}',
    lemmas                      TEXT[]          NOT NULL DEFAULT '{}',
    priority                    VARCHAR(50)     NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    category                    VARCHAR(100)    NOT NULL DEFAULT 'General' CHECK (category IN ('Bug', 'Feature Request', 'Improvement', 'Complaint', 'General')),
    product_name                VARCHAR(255),
    product_version             VARCHAR(100),
    tags                        TEXT[],
    sentiment_self_reported     VARCHAR(50) CHECK (sentiment_self_reported IN ('Positive', 'Negative', 'Neutral') OR sentiment_self_reported IS NULL),
    language                    VARCHAR(10)     NOT NULL DEFAULT 'en',
    submission_date             DATE,
    weight                      INTEGER         NOT NULL DEFAULT 1 CHECK (weight >= 1),
    duplicate_group_id          UUID            NOT NULL,
    word_count                  INTEGER         NOT NULL DEFAULT 0,
    char_count                  INTEGER         NOT NULL DEFAULT 0,
    token_count                 INTEGER         NOT NULL DEFAULT 0,
    lemma_count                 INTEGER         NOT NULL DEFAULT 0,
    processing_metadata         JSONB           NOT NULL DEFAULT '{}',
    processing_status           VARCHAR(50)     NOT NULL DEFAULT 'processed' CHECK (processing_status IN ('processed', 'failed', 'reprocessing')),
    processing_error            TEXT,
    search_vector               TSVECTOR,
    processing_timestamp        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ready_for_classification    BOOLEAN         NOT NULL DEFAULT TRUE,
    classified_at               TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_feedback_ready         ON processed_feedback (ready_for_classification, classified_at) WHERE ready_for_classification = TRUE AND classified_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_processed_feedback_project_id    ON processed_feedback (project_id);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_dup_group     ON processed_feedback (duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_weight        ON processed_feedback (weight DESC);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_category      ON processed_feedback (category);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_priority      ON processed_feedback (priority);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_raw_id        ON processed_feedback (raw_feedback_id);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_fts           ON processed_feedback USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_status        ON processed_feedback (processing_status);
CREATE INDEX IF NOT EXISTS idx_processed_feedback_ts            ON processed_feedback (processing_timestamp DESC);

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update search_vector
CREATE OR REPLACE FUNCTION update_processed_feedback_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.original_subject, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.clean_text, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_processed_feedback_search_vector ON processed_feedback;
CREATE TRIGGER trg_processed_feedback_search_vector
    BEFORE INSERT OR UPDATE OF original_subject, clean_text
    ON processed_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_processed_feedback_search_vector();

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_raw_feedback_updated_at ON raw_feedback;
CREATE TRIGGER trg_raw_feedback_updated_at
    BEFORE UPDATE ON raw_feedback FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_processed_feedback_updated_at ON processed_feedback;
CREATE TRIGGER trg_processed_feedback_updated_at
    BEFORE UPDATE ON processed_feedback FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- END OF MIGRATION
-- ============================================================
```

---

*End of schema.md — AI Product Manager Copilot PostgreSQL Schema for Modules 1–3*
