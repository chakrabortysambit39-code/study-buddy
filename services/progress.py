from datetime import date, timedelta
from services.database import connection


def record(user_id, kind, xp, score=None, total=None):
    with connection() as conn:
        conn.execute("INSERT INTO activity (user_id, kind, xp, score, total) VALUES (%s, %s, %s, %s, %s)", (user_id, kind, xp, score, total))


def stats(user_id):
    with connection() as conn:
        row = conn.execute("SELECT COALESCE(SUM(xp),0) AS xp, COUNT(CASE WHEN kind LIKE '%%quiz%%' THEN 1 END) AS quizzes, COALESCE(SUM(score),0) AS score, COALESCE(SUM(total),0) AS total FROM activity WHERE user_id = %s", (user_id,)).fetchone()
        days = conn.execute("SELECT DISTINCT (created_at AT TIME ZONE 'UTC')::date AS day FROM activity WHERE user_id = %s ORDER BY day DESC", (user_id,)).fetchall()
    active_days = {r["day"] for r in days if r["day"]}
    streak = 0
    current = date.today()
    if current not in active_days and current - timedelta(days=1) in active_days:
        current -= timedelta(days=1)
    while current in active_days:
        streak += 1
        current -= timedelta(days=1)
    xp = row["xp"] or 0
    return {"xp": xp, "level": xp // 100 + 1, "level_progress": xp % 100, "quizzes": row["quizzes"] or 0, "accuracy": round((row["score"] / row["total"]) * 100) if row["total"] else 0, "streak": streak}
