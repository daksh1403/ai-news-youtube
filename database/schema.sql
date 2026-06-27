CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    type TEXT CHECK(type IN ('rss', 'api', 'scraper')),
    category TEXT DEFAULT 'general',
    reliability_score REAL DEFAULT 0.5,
    last_fetched TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER REFERENCES sources(id),
    external_id TEXT,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    url TEXT,
    author TEXT,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    language TEXT DEFAULT 'en',
    word_count INTEGER,
    UNIQUE(source_id, external_id)
);

CREATE TABLE IF NOT EXISTS used_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_url TEXT NOT NULL UNIQUE,
    article_title TEXT,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    video_path TEXT,
    youtube_video_id TEXT
);

CREATE TABLE IF NOT EXISTS article_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id),
    chunk_index INTEGER,
    chunk_text TEXT,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(title, content, summary);

CREATE TABLE IF NOT EXISTS trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    velocity REAL,
    impact REAL,
    novelty REAL,
    combined_score REAL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    article_ids TEXT
);

CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT,
    hook TEXT,
    full_script TEXT,
    word_count INTEGER,
    estimated_duration INTEGER,
    sections TEXT,
    cta TEXT,
    quality_score REAL,
    approved INTEGER DEFAULT 0,
    revision_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS thumbnails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER,
    prompt TEXT,
    image_path TEXT,
    text_overlay TEXT,
    style TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seo_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER,
    title TEXT,
    description TEXT,
    tags TEXT,
    hashtags TEXT,
    category TEXT,
    optimized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER,
    file_path TEXT,
    voice TEXT,
    duration REAL,
    file_size INTEGER,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER,
    file_path TEXT,
    resolution TEXT,
    fps INTEGER,
    duration REAL,
    file_size INTEGER,
    format TEXT DEFAULT 'shorts',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT,
    youtube_video_id TEXT,
    youtube_url TEXT,
    title TEXT,
    description TEXT,
    tags TEXT,
    category TEXT,
    privacy_status TEXT DEFAULT 'public',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    upload_status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id TEXT,
    views INTEGER DEFAULT 0,
    watch_time_seconds REAL DEFAULT 0,
    average_view_duration REAL DEFAULT 0,
    click_through_rate REAL DEFAULT 0,
    subscriber_growth INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type TEXT,
    insight_data TEXT,
    confidence REAL,
    applied INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT CHECK(status IN ('running', 'completed', 'failed', 'partial')),
    articles_collected INTEGER,
    scripts_generated INTEGER,
    videos_produced INTEGER,
    videos_uploaded INTEGER,
    errors TEXT,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT,
    memory_type TEXT CHECK(memory_type IN ('short_term', 'long_term', 'episodic')),
    content TEXT,
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_used_articles_url ON used_articles(article_url);
CREATE INDEX IF NOT EXISTS idx_used_articles_date ON used_articles(used_at);
CREATE INDEX IF NOT EXISTS idx_scripts_approved ON scripts(approved);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(upload_status);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics(collected_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_id ON pipeline_runs(run_id);
