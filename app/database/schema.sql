DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS refresh_sessions CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS expense_categories CASCADE;
DROP TABLE IF EXISTS recurring_expenses CASCADE;
DROP TYPE IF EXISTS occurrence CASCADE;
DROP TABLE IF EXISTS todos CASCADE;


CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(80),
    bio VARCHAR(280),
    avatar_data BYTEA,
    avatar_content_type VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE refresh_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ,
    user_agent VARCHAR(500)
);

CREATE INDEX refresh_sessions_user_id_idx ON refresh_sessions(user_id);
CREATE INDEX refresh_sessions_family_id_idx ON refresh_sessions(family_id);


CREATE TYPE occurrence AS ENUM (
    'NONE',
    'DAILY',
    'WEEKLY',
    'MONTHLY',
    'YEARLY'
);

CREATE TABLE expense_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES expense_categories(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(30) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expense_date DATE NOT NULL,
    recurrence occurrence NOT NULL DEFAULT 'NONE'
);

CREATE TABLE recurring_expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES expense_categories(id),
    title VARCHAR(120) NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    frequency occurrence NOT NULL CHECK (frequency <> 'NONE'),
    start_date DATE NOT NULL,
    end_date DATE,
    cancellation_difficulty VARCHAR(20) NOT NULL DEFAULT 'EASY'
        CHECK (cancellation_difficulty IN ('EASY', 'NOTICE_REQUIRED', 'CONTRACT_LOCKED', 'NON_CANCELLABLE', 'ESSENTIAL')),
    cancellable_from DATE,
    cancellation_notes VARCHAR(280),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date IS NULL OR end_date >= start_date),
    CHECK (cancellable_from IS NULL OR cancellable_from >= start_date),
    CHECK (cancellable_from IS NULL OR cancellation_difficulty IN ('NOTICE_REQUIRED', 'CONTRACT_LOCKED'))
);

CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    description TEXT,
    priority VARCHAR(2) NOT NULL DEFAULT 'P3',
    status VARCHAR(20) NOT NULL default 'not_started',
    due_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    source VARCHAR(50) DEFAULT 'manual'
);
