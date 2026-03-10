-- Scout AI Schema Extension: Signal Clusters and Predictions
-- Adds tables for the clustering engine and prediction service.

-- ── Signal Clusters ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signal_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cluster_title VARCHAR(500) NOT NULL,
    cluster_description TEXT,
    confidence_score FLOAT DEFAULT 0.5,
    impact_score FLOAT DEFAULT 0.5,
    signal_count INTEGER DEFAULT 0,
    source_types JSONB DEFAULT '[]',
    related_signal_ids JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_clusters_user_id ON signal_clusters(user_id);
CREATE INDEX IF NOT EXISTS idx_signal_clusters_impact ON signal_clusters(impact_score DESC);
CREATE INDEX IF NOT EXISTS idx_signal_clusters_created ON signal_clusters(created_at DESC);

-- ── Predictions ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE SET NULL,
    cluster_id UUID REFERENCES signal_clusters(id) ON DELETE SET NULL,
    prediction TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    timeline VARCHAR(255),
    category VARCHAR(100),  -- product_launch | pricing_change | market_expansion | etc.
    evidence JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'active',  -- active | confirmed | invalidated | expired
    outcome TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_competitor ON predictions(competitor_id);
CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(status);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at DESC);
