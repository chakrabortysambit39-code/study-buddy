from services.database import connection


def list_notes(user_id):
    with connection() as conn:
        return conn.execute("SELECT id, title, subject, content, created_at FROM notes WHERE user_id = %s ORDER BY id DESC", (user_id,)).fetchall()


def create_note(user_id, title, subject, content):
    with connection() as conn:
        row = conn.execute("INSERT INTO notes (user_id, title, subject, content) VALUES (%s, %s, %s, %s) RETURNING id", (user_id, title, subject, content)).fetchone()
        return row["id"]


def delete_note(user_id, note_id):
    with connection() as conn:
        conn.execute("DELETE FROM notes WHERE id = %s AND user_id = %s", (note_id, user_id))
