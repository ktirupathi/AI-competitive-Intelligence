-- Scout AI Database Schema
-- PostgreSQL with pgvector extension

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    plan VARCHAR(50) NOT NULL DEFAULT 'starter',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    max_competitors INTEGER NOT NULL DEFAULT 3,
    slack_webhook_url TEXT,
    slack_channel_id VARCHAR(255),
    email_notifications BOOLEAN NOT NULL DEFAULT true,
    slack_notifications BOOLEAN NOT NULL DEFAULT false,
    webhook_url TEXT,
    briefing_day VARCHAR(10) NOT NULL DEFAULT 'monday',
    briefing_time TIME NOT NULL DEFAULT '09:00:00',
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Competitors ──────────────────────────────────────────────────────────────

CREATE TABLE competitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    logo_url TEXT,
    description TEXT,
    industry VARCHAR(255),
    employee_count VARCHAR(50),
    funding_stage VARCHAR(100),
    headquarters VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_scanned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, domain)
);

CREATE INDEX idx_competitors_user_id ON competitors(user_id);

-- ── Snapshots (website captures) ─────────────────────────────────────────────

CREATE TABLE snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    content_text TEXT,
    html_s3_key TEXT,
    screenshot_s3_key TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_snapshots_competitor_id ON snapshots(competitor_id);
CREATE INDEX idx_snapshots_created_at ON snapshots(created_at DESC);

-- ── Changes (detected diffs) ─────────────────────────────────────────────────

CREATE TABLE changes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    snapshot_id UUID REFERENCES snapshots(id) ON DELETE SET NULL,
    source VARCHAR(50) NOT NULL, -- website, pricing, product, messaging
    change_type VARCHAR(50) NOT NULL, -- added, removed, modified
    title VARCHAR(500) NOT NULL,
    description TEXT,
    significance VARCHAR(20) NOT NULL DEFAULT 'low', -- low, medium, high, critical
    diff_data JSONB DEFAULT '{}',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_changes_competitor_id ON changes(competitor_id);
CREATE INDEX idx_changes_significance ON changes(significance);

-- ── News Items ───────────────────────────────────────────────────────────────

CREATE TABLE news_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    url TEXT,
    source VARCHAR(255),
    summary TEXT,
    sentiment VARCHAR(20), -- positive, neutral, negative
    relevance_score FLOAT DEFAULT 0.0,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_competitor_id ON news_items(competitor_id);
CREATE INDEX idx_news_published_at ON news_items(published_at DESC);

-- ── Job Postings ─────────────────────────────────────────────────────────────

CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    department VARCHAR(255),
    location VARCHAR(255),
    url TEXT,
    description TEXT,
    seniority VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_competitor_id ON job_postings(competitor_id);

-- ── Reviews ──────────────────────────────────────────────────────────────────

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    platform VARCHAR(100) NOT NULL, -- g2, capterra, trustpilot
    reviewer_name VARCHAR(255),
    rating FLOAT,
    title VARCHAR(500),
    content TEXT,
    pros TEXT,
    cons TEXT,
    review_url TEXT,
    review_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reviews_competitor_id ON reviews(competitor_id);
CREATE INDEX idx_reviews_platform ON reviews(platform);

-- ── Social Posts ─────────────────────────────────────────────────────────────

CREATE TABLE social_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_id UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- linkedin, twitter
    post_url TEXT,
    content TEXT,
    engagement_count INTEGER DEFAULT 0,
    post_type VARCHAR(50), -- announcement, hiring, product, thought_leadership
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_competitor_id ON social_posts(competitor_id);
CREATE INDEX idx_social_platform ON social_posts(platform);

-- ── Insights ─────────────────────────────────────────────────────────────────

CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES competitors(id) ON DELETE SET NULL,
    briefing_id UUID, -- set after briefing created
    category VARCHAR(100) NOT NULL, -- product, pricing, hiring, marketing, strategy
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    impact_score FLOAT NOT NULL DEFAULT 0.0, -- 0.0 to 1.0
    confidence_score FLOAT NOT NULL DEFAULT 0.0, -- 0.0 to 1.0
    signal_type VARCHAR(50), -- trend, anomaly, prediction
    sources JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_insights_user_id ON insights(user_id);
CREATE INDEX idx_insights_briefing_id ON insights(briefing_id);
CREATE INDEX idx_insights_impact ON insights(impact_score DESC);

-- ── Briefings ────────────────────────────────────────────────────────────────

CREATE TABLE briefings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    executive_summary TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    top_insights JSONB NOT NULL DEFAULT '[]',
    predictive_signals JSONB NOT NULL DEFAULT '[]',
    recommended_plays JSONB NOT NULL DEFAULT '[]',
    competitor_summaries JSONB NOT NULL DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- draft, published, delivered
    delivered_via JSONB DEFAULT '[]', -- ["email", "slack"]
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_briefings_user_id ON briefings(user_id);
CREATE INDEX idx_briefings_status ON briefings(status);
CREATE INDEX idx_briefings_created_at ON briefings(created_at DESC);

-- Add foreign key for insights -> briefings
ALTER TABLE insights ADD CONSTRAINT fk_insights_briefing
    FOREIGN KEY (briefing_id) REFERENCES briefings(id) ON DELETE SET NULL;

-- ── Embeddings ───────────────────────────────────────────────────────────────

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50) NOT NULL, -- snapshot, news, review, social, insight
    source_id UUID NOT NULL,
    content_text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embeddings_source ON embeddings(source_type, source_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── Integrations ─────────────────────────────────────────────────────────────

CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- slack, email, webhook
    is_active BOOLEAN NOT NULL DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

CREATE INDEX idx_integrations_user_id ON integrations(user_id);

-- ── Updated-at trigger ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_competitors_updated_at BEFORE UPDATE ON competitors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_briefings_updated_at BEFORE UPDATE ON briefings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_integrations_updated_at BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
