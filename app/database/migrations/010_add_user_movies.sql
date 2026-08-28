CREATE TABLE IF NOT EXISTS user_movies (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    imdb_id VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    year VARCHAR(20),
    poster_url TEXT,
    plot TEXT,
    director TEXT,
    actors TEXT,
    genre TEXT,
    runtime VARCHAR(40),
    content_rating VARCHAR(30),
    released VARCHAR(40),
    awards TEXT,
    country TEXT,
    language TEXT,
    box_office VARCHAR(80),
    external_ratings JSONB NOT NULL DEFAULT '[]'::jsonb,
    list_status VARCHAR(20) NOT NULL DEFAULT 'WANT_TO_WATCH'
        CHECK (list_status IN ('WANT_TO_WATCH', 'WATCHED')),
    personal_rating NUMERIC(3,1)
        CHECK (personal_rating IS NULL OR (personal_rating >= 1 AND personal_rating <= 10)),
    critique VARCHAR(2000),
    watched_at DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, imdb_id),
    CHECK (list_status = 'WATCHED' OR (personal_rating IS NULL AND watched_at IS NULL))
);

CREATE INDEX IF NOT EXISTS user_movies_user_status_idx
    ON user_movies(user_id, list_status);

ALTER TABLE user_movies ADD COLUMN IF NOT EXISTS released VARCHAR(40);
ALTER TABLE user_movies ADD COLUMN IF NOT EXISTS awards TEXT;
ALTER TABLE user_movies ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE user_movies ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE user_movies ADD COLUMN IF NOT EXISTS box_office VARCHAR(80);
