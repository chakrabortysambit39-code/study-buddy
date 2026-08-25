import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")

class DatabaseNotConfigured(RuntimeError):
    pass


def _dsn():
    if not DATABASE_URL:
        raise DatabaseNotConfigured("DATABASE_URL is not configured. Create a Render PostgreSQL database and add its internal URL to the web service environment.")
    return DATABASE_URL


@contextmanager
def connection():
    conn = psycopg.connect(_dsn(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS notes (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS activity (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            score INTEGER,
            total INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS notes_user_idx ON notes(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS activity_user_idx ON activity(user_id)")


def find_user_by_email(email):
    with connection() as conn:
        return conn.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s", (email,)).fetchone()


def create_user(name, email, password_hash):
    with connection() as conn:
        return conn.execute("INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name, email", (name, email, password_hash)).fetchone()


# Database initialization is attempted when DATABASE_URL is present.
# The web app can still boot so Render can show a useful configuration message.
if DATABASE_URL:
    init_db()
