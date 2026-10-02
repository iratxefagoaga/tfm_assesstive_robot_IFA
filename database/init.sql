CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_episodes (
    memory_id VARCHAR(20) PRIMARY KEY,

    user_id VARCHAR(100) NOT NULL,

    timestamp TIMESTAMP NOT NULL,

    location VARCHAR(150),

    task VARCHAR(150),

    goal TEXT,

    observation TEXT,

    action TEXT,

    outcome TEXT,

    preference TEXT,

    memory_type TEXT[],

    importance DOUBLE PRECISION DEFAULT 0.5,

    confidence DOUBLE PRECISION DEFAULT 1.0,

    textual_summary TEXT NOT NULL,

    metadata JSONB DEFAULT '{}'::jsonb,

    embedding VECTOR(1024),

    episodic_embedding VECTOR(1024)
);
CREATE INDEX idx_memory_user
ON memory_episodes(user_id);

CREATE INDEX idx_memory_location
ON memory_episodes(location);

CREATE INDEX idx_memory_task
ON memory_episodes(task);

CREATE INDEX idx_memory_timestamp
ON memory_episodes(timestamp);
