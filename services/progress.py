import os
import sqlite3
from datetime import date, timedelta

DB_PATH = os.getenv("STUDY_BUDDY_DB", "study_buddy.db")


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with _connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            score INTEGER,
            total INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")


def record(kind, xp, score=None, total=None):
    with _connect() as connection:
        connection.execute("INSERT INTO activity (kind, xp, score, total) VALUES (?, ?, ?, ?)", (kind, xp, score, total))


def stats():
    with _connect() as connection:
        row = connection.execute("SELECT COALESCE(SUM(xp),0) xp, COUNT(CASE WHEN kind LIKE '%quiz%' THEN 1 END) quizzes, COALESCE(SUM(score),0) score, COALESCE(SUM(total),0) total FROM activity").fetchone()
        days = connection.execute("SELECT DISTINCT date(created_at) day FROM activity ORDER BY day DESC").fetchall()
    active_days = {date.fromisoformat(r["day"]) for r in days if r["day"]}
    streak = 0
    current = date.today()
    if current not in active_days and current - timedelta(days=1) in active_days:
        current -= timedelta(days=1)
    while current in active_days:
        streak += 1
        current -= timedelta(days=1)
    xp = row["xp"] or 0
    return {
        "xp": xp,
        "level": xp // 100 + 1,
        "level_progress": xp % 100,
        "quizzes": row["quizzes"] or 0,
        "accuracy": round((row["score"] / row["total"]) * 100) if row["total"] else 0,
        "streak": streak,
    }


init_db()
