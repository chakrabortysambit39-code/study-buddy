import os
import sqlite3

DB_PATH = os.getenv("STUDY_BUDDY_DB", "study_buddy.db")


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with _connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")


def list_notes():
    with _connect() as connection:
        return connection.execute("SELECT id, title, subject, content, created_at FROM notes ORDER BY id DESC").fetchall()


def create_note(title, subject, content):
    with _connect() as connection:
        cursor = connection.execute("INSERT INTO notes (title, subject, content) VALUES (?, ?, ?)", (title, subject, content))
        return cursor.lastrowid


def delete_note(note_id):
    with _connect() as connection:
        connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))


init_db()
