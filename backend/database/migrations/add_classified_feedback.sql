-- ============================================================
-- AI Product Manager Copilot — Module 4 Migration
-- Table: classified_feedback
-- Version: 1.1.0
-- ============================================================

-- ============================================================
-- TABLE: classified_feedback
-- Stores AI-generated classification, sentiment, themes,
-- keywords, pain points, and customer intent for each
-- processed feedback record.
-- ============================================================
CREATE TABLE IF NOT EXISTS classified_feedback (
    -- =========================================================
    -- PRIMARY KEY
    -- =========================================================
    classified_id               UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- =========================================================
    -- LINK TO PROCESSED FEEDBACK
    -- =========================================================
    processed_feedback_id       UUID            NOT NULL UNIQUE
                                    REFERENCES processed_feedback(processed_id) ON DELETE CASCADE,
    -- One-to-one: each processed_feedback record produces at most one classified_feedback

    -- =========================================================
    -- PROJECT ASSOCIATION (inherited)
    -- =========================================================
    project_id                  UUID            NOT NULL,

    -- =========================================================
    -- AI CLASSIFICATION OUTPUT
    -- =========================================================
    ai_category                 VARCHAR(100)    NOT NULL
                                    CHECK (ai_category IN (
                                        'Bug Report',
                                        'Feature Request',
                                        'Complaint',
                                        'Praise',
                                        'Question',
                                        'Pricing Issue',
                                        'Performance Issue',
                                        'UI Issue',
                                        'Security Concern'
                                    )),

    ai_confidence_score         FLOAT           NOT NULL DEFAULT 0.0
                                    CHECK (ai_confidence_score >= 0.0 AND ai_confidence_score <= 1.0),
    -- Gemini's confidence in the primary classification (0.0 – 1.0)

    -- =========================================================
    -- AI SENTIMENT ANALYSIS
    -- =========================================================
    ai_sentiment                VARCHAR(50)     NOT NULL DEFAULT 'Neutral'
                                    CHECK (ai_sentiment IN ('Positive', 'Negative', 'Neutral', 'Mixed')),

    ai_sentiment_score          FLOAT           NOT NULL DEFAULT 0.0
                                    CHECK (ai_sentiment_score >= -1.0 AND ai_sentiment_score <= 1.0),
    -- Sentiment intensity: -1.0 (very negative) to 1.0 (very positive)

    -- =========================================================
    -- EXTRACTED: TOPICS, THEMES, KEYWORDS
    -- =========================================================
    topics                      TEXT[]          NOT NULL DEFAULT '{}',
    -- High-level subject areas identified by Gemini

    themes                      TEXT[]          NOT NULL DEFAULT '{}',
    -- Recurring patterns or themes across feedback

    keywords                    TEXT[]          NOT NULL DEFAULT '{}',
    -- Important terms extracted from the text

    -- =========================================================
    -- PAIN POINTS & CUSTOMER INTENT
    -- =========================================================
    pain_points                 TEXT[]          NOT NULL DEFAULT '{}',
    -- Specific user frustrations or problems

    customer_intent             VARCHAR(500),
    -- What the customer is trying to achieve (e.g., "wants faster load times")

    -- =========================================================
    -- AI SUMMARY
    -- =========================================================
    ai_summary                  TEXT,
    -- Gemini-generated concise summary of the feedback

    -- =========================================================
    -- WEIGHT (inherited from processed_feedback)
    -- =========================================================
    weight                      INTEGER         NOT NULL DEFAULT 1
                                    CHECK (weight >= 1),

    -- =========================================================
    -- CLASSIFICATION METADATA (JSONB)
    -- =========================================================
    classification_metadata     JSONB           NOT NULL DEFAULT '{}',
    -- Structure:
    -- {
    --   "gemini_model": "gemini-2.0-flash",
    --   "prompt_version": "1.0.0",
    --   "classification_duration_ms": 850,
    --   "token_usage": { "prompt_tokens": 500, "completion_tokens": 200 }
    -- }

    -- =========================================================
    -- CLASSIFICATION STATUS
    -- =========================================================
    classification_status       VARCHAR(50)     NOT NULL DEFAULT 'classified'
                                    CHECK (classification_status IN ('classified', 'failed')),
    classification_error        TEXT,
    -- NULL if successful; error message if classification_status = 'failed'

    -- =========================================================
    -- TIMESTAMPS
    -- =========================================================
    classified_at               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- For filtering by project
CREATE INDEX IF NOT EXISTS idx_classified_feedback_project_id
    ON classified_feedback (project_id);

-- For filtering by AI category
CREATE INDEX IF NOT EXISTS idx_classified_feedback_ai_category
    ON classified_feedback (ai_category);

-- For filtering by AI sentiment
CREATE INDEX IF NOT EXISTS idx_classified_feedback_ai_sentiment
    ON classified_feedback (ai_sentiment);

-- For sorting by weight (high-demand items float to top)
CREATE INDEX IF NOT EXISTS idx_classified_feedback_weight
    ON classified_feedback (weight DESC);

-- For linking back to processed feedback
CREATE INDEX IF NOT EXISTS idx_classified_feedback_processed_id
    ON classified_feedback (processed_feedback_id);

-- For classification status filtering
CREATE INDEX IF NOT EXISTS idx_classified_feedback_status
    ON classified_feedback (classification_status);

-- For timestamp-based sorting
CREATE INDEX IF NOT EXISTS idx_classified_feedback_classified_at
    ON classified_feedback (classified_at DESC);

-- GIN index for array-based queries on topics, themes, keywords, pain_points
CREATE INDEX IF NOT EXISTS idx_classified_feedback_topics_gin
    ON classified_feedback USING GIN (topics);

CREATE INDEX IF NOT EXISTS idx_classified_feedback_themes_gin
    ON classified_feedback USING GIN (themes);

CREATE INDEX IF NOT EXISTS idx_classified_feedback_keywords_gin
    ON classified_feedback USING GIN (keywords);

CREATE INDEX IF NOT EXISTS idx_classified_feedback_pain_points_gin
    ON classified_feedback USING GIN (pain_points);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_classified_feedback_metadata_gin
    ON classified_feedback USING GIN (classification_metadata);

-- ============================================================
-- TRIGGER: Auto-update updated_at on row modification
-- ============================================================
-- Reuses the existing update_updated_at_column() function from init_schema.sql

DROP TRIGGER IF EXISTS trg_classified_feedback_updated_at ON classified_feedback;
CREATE TRIGGER trg_classified_feedback_updated_at
    BEFORE UPDATE ON classified_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- COMMENTS
-- ============================================================
COMMENT ON TABLE  classified_feedback                               IS 'AI-classified feedback records. One row per processed_feedback. Generated by Module 4 using Gemini.';
COMMENT ON COLUMN classified_feedback.classified_id                 IS 'Unique UUID for this classified record';
COMMENT ON COLUMN classified_feedback.processed_feedback_id         IS 'FK to the processed_feedback record this classification was derived from';
COMMENT ON COLUMN classified_feedback.project_id                    IS 'UUID of the product/project (inherited from processed_feedback)';
COMMENT ON COLUMN classified_feedback.ai_category                   IS 'AI-assigned category: Bug Report, Feature Request, Complaint, Praise, Question, Pricing Issue, Performance Issue, UI Issue, Security Concern';
COMMENT ON COLUMN classified_feedback.ai_confidence_score           IS 'AI confidence in the classification (0.0 to 1.0)';
COMMENT ON COLUMN classified_feedback.ai_sentiment                  IS 'AI-determined sentiment: Positive, Negative, Neutral, Mixed';
COMMENT ON COLUMN classified_feedback.ai_sentiment_score            IS 'Sentiment intensity score (-1.0 to 1.0)';
COMMENT ON COLUMN classified_feedback.topics                        IS 'Array of high-level subject areas identified by AI';
COMMENT ON COLUMN classified_feedback.themes                        IS 'Array of recurring patterns or themes';
COMMENT ON COLUMN classified_feedback.keywords                      IS 'Array of important terms extracted from feedback text';
COMMENT ON COLUMN classified_feedback.pain_points                   IS 'Array of specific user frustrations or problems';
COMMENT ON COLUMN classified_feedback.customer_intent               IS 'What the customer is trying to achieve';
COMMENT ON COLUMN classified_feedback.ai_summary                    IS 'AI-generated concise summary of the feedback';
COMMENT ON COLUMN classified_feedback.weight                        IS 'Semantic frequency weight (inherited from processed_feedback)';
COMMENT ON COLUMN classified_feedback.classification_metadata       IS 'JSONB: Gemini model, prompt version, processing duration, token usage';
COMMENT ON COLUMN classified_feedback.classification_status         IS 'classified = success; failed = error occurred';
COMMENT ON COLUMN classified_feedback.classification_error          IS 'Error message if classification_status = failed';
COMMENT ON COLUMN classified_feedback.classified_at                 IS 'UTC timestamp when Gemini classification completed';

-- ============================================================
-- END OF MODULE 4 MIGRATION
-- ============================================================
