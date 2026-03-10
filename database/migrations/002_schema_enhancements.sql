-- Scout AI Schema Enhancements
-- Aligns the database with the SQLAlchemy ORM models and adds
-- performance indexes for the new monitoring tasks.

-- ── Ensure pgvector extension exists ──────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "vector";

-- ── Add missing columns to users table ───────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS company_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_competitor_limit INTEGER NOT NULL DEFAULT 3;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_prefs JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS briefing_frequency VARCHAR(20) NOT NULL DEFAULT 'weekly';

-- ── Add missing columns to competitors table ─────────────────────────────
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS track_website BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS track_news BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS track_jobs BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS track_reviews BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS track_social BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS social_links JSONB DEFAULT '{}';
ALTER TABLE competitors ADD COLUMN IF NOT EXISTS last_crawled_at TIMESTAMPTZ;

-- ── Add missing columns to snapshots table ───────────────────────────────
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS page_type VARCHAR(50) DEFAULT 'homepage';
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS raw_html TEXT;
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS markdown_content TEXT;
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS metadata_extracted JSONB DEFAULT '{}';
ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ── Add missing columns to changes table ─────────────────────────────────
ALTER TABLE changes ADD COLUMN IF NOT EXISTS snapshot_before_id UUID REFERENCES snapshots(id) ON DELETE SET NULL;
ALTER TABLE changes ADD COLUMN IF NOT EXISTS snapshot_after_id UUID REFERENCES snapshots(id) ON DELETE SET NULL;
ALTER TABLE changes ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'medium';
ALTER TABLE changes ADD COLUMN IF NOT EXISTS significance_score FLOAT DEFAULT 0.5;
ALTER TABLE changes ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE changes ADD COLUMN IF NOT EXISTS diff_detail JSONB DEFAULT '{}';
ALTER TABLE changes ADD COLUMN IF NOT EXISTS page_url TEXT;

-- ── Add missing columns to news_items table ──────────────────────────────
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS author VARCHAR(255);
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS categories JSONB DEFAULT '[]';
ALTER TABLE news_items ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ── Add missing columns to job_postings table ────────────────────────────
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS employment_type VARCHAR(50);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS seniority_level VARCHAR(50);
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]';
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS salary_range JSONB;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS posted_at TIMESTAMPTZ;
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE job_postings ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

-- ── Add missing columns to reviews table ─────────────────────────────────
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS star_rating INTEGER;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS body TEXT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20);
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ── Add missing columns to social_posts table ────────────────────────────
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS media_urls JSONB DEFAULT '[]';
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS likes INTEGER DEFAULT 0;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS shares INTEGER DEFAULT 0;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS comments_count INTEGER DEFAULT 0;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS engagement_rate FLOAT;
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20);
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS topics JSONB DEFAULT '[]';
ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ── Add missing columns to insights table ────────────────────────────────
ALTER TABLE insights ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'medium';
ALTER TABLE insights ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.8;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS detail TEXT;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS recommended_action TEXT;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS source_refs JSONB DEFAULT '{}';
ALTER TABLE insights ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT false;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS is_dismissed BOOLEAN DEFAULT false;
ALTER TABLE insights ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ── Add missing columns to briefings table ───────────────────────────────
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS frequency VARCHAR(20) DEFAULT 'weekly';
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS full_content TEXT;
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS sections JSONB DEFAULT '{}';
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS delivery_channels JSONB DEFAULT '[]';
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS competitor_count INTEGER DEFAULT 0;
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS insight_count INTEGER DEFAULT 0;
ALTER TABLE briefings ADD COLUMN IF NOT EXISTS change_count INTEGER DEFAULT 0;

-- ── Add missing columns to integrations table ────────────────────────────
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS type VARCHAR(50);
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS slack_channel_id VARCHAR(255);
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS slack_workspace_id VARCHAR(255);
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS slack_access_token TEXT;
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_address VARCHAR(320);
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS webhook_url TEXT;
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS webhook_secret VARCHAR(255);
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS event_filters JSONB DEFAULT '{}';

-- ── Add missing columns to embeddings table ──────────────────────────────
ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS model VARCHAR(100) DEFAULT 'text-embedding-3-small';

-- ── Additional performance indexes ───────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_changes_detected_at ON changes(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_changes_significance_score ON changes(significance_score DESC);
CREATE INDEX IF NOT EXISTS idx_news_relevance ON news_items(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_news_discovered_at ON news_items(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON job_postings(competitor_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_jobs_discovered_at ON job_postings(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_discovered_at ON reviews(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews(sentiment);
CREATE INDEX IF NOT EXISTS idx_social_discovered_at ON social_posts(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_insights_severity ON insights(severity);
CREATE INDEX IF NOT EXISTS idx_insights_is_read ON insights(is_read) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_briefings_user_status ON briefings(user_id, status);

-- ── HNSW index for embeddings (faster than IVFFlat for small-medium datasets) ─
-- Use this instead of the IVFFlat index if your dataset is < 1M rows
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw
    ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
