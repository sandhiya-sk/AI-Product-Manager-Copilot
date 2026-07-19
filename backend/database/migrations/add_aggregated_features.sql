-- ==========================================================================
-- Migration: Add aggregated_features table
-- Module 5: Feature Request Aggregation
-- ==========================================================================

-- 1. Create the aggregated_features table
CREATE TABLE IF NOT EXISTS aggregated_features (
    -- Primary Key
    aggregate_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Project Association
    project_id          UUID NOT NULL,

    -- Cluster Identity (AI-generated)
    cluster_label       VARCHAR(255) NOT NULL,
    cluster_description TEXT,

    -- Aggregation Metrics
    frequency           INTEGER NOT NULL DEFAULT 1
        CONSTRAINT chk_agg_frequency CHECK (frequency >= 1),
    importance          VARCHAR(50) NOT NULL DEFAULT 'Medium'
        CONSTRAINT chk_agg_importance CHECK (importance IN ('Critical', 'High', 'Medium', 'Low')),
    affected_users      INTEGER NOT NULL DEFAULT 0
        CONSTRAINT chk_agg_affected_users CHECK (affected_users >= 0),

    -- Sentiment Aggregation
    avg_sentiment_score FLOAT NOT NULL DEFAULT 0.0
        CONSTRAINT chk_agg_sentiment_score_range CHECK (avg_sentiment_score >= -1.0 AND avg_sentiment_score <= 1.0),
    dominant_sentiment  VARCHAR(50) NOT NULL DEFAULT 'Neutral'
        CONSTRAINT chk_agg_dominant_sentiment CHECK (dominant_sentiment IN ('Positive', 'Negative', 'Neutral', 'Mixed')),

    -- Extracted Data
    representative_keywords TEXT[] NOT NULL DEFAULT '{}',
    sample_feedback_ids     UUID[] NOT NULL DEFAULT '{}',
    member_classified_ids   UUID[] NOT NULL DEFAULT '{}',

    -- Trend Detection
    trend_direction     VARCHAR(50) NOT NULL DEFAULT 'stable'
        CONSTRAINT chk_agg_trend_direction CHECK (trend_direction IN ('rising', 'stable', 'declining')),
    trend_details       JSONB NOT NULL DEFAULT '{}',

    -- Aggregation Metadata
    aggregation_metadata JSONB NOT NULL DEFAULT '{}',
    aggregation_status   VARCHAR(50) NOT NULL DEFAULT 'aggregated'
        CONSTRAINT chk_agg_status CHECK (aggregation_status IN ('aggregated', 'failed')),
    aggregation_error    TEXT,

    -- Timestamps
    aggregated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_agg_project_id
    ON aggregated_features (project_id);

CREATE INDEX IF NOT EXISTS idx_agg_importance
    ON aggregated_features (importance);

CREATE INDEX IF NOT EXISTS idx_agg_frequency_desc
    ON aggregated_features (frequency DESC);

CREATE INDEX IF NOT EXISTS idx_agg_trend_direction
    ON aggregated_features (trend_direction);

CREATE INDEX IF NOT EXISTS idx_agg_project_importance
    ON aggregated_features (project_id, importance);

-- 3. Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_aggregated_features_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_aggregated_features_updated_at ON aggregated_features;
CREATE TRIGGER trg_aggregated_features_updated_at
    BEFORE UPDATE ON aggregated_features
    FOR EACH ROW
    EXECUTE FUNCTION update_aggregated_features_updated_at();

-- 4. Helpful comments
COMMENT ON TABLE aggregated_features IS 'Module 5: AI-clustered feature request aggregation';
COMMENT ON COLUMN aggregated_features.cluster_label IS 'AI-generated cluster name (e.g., Dark Mode)';
COMMENT ON COLUMN aggregated_features.frequency IS 'Total weighted count of requests in this cluster';
COMMENT ON COLUMN aggregated_features.importance IS 'AI-derived importance: Critical/High/Medium/Low';
COMMENT ON COLUMN aggregated_features.affected_users IS 'Distinct user count across cluster members';
COMMENT ON COLUMN aggregated_features.trend_direction IS 'Request trend: rising/stable/declining';
COMMENT ON COLUMN aggregated_features.member_classified_ids IS 'All classified_feedback IDs in this cluster';
