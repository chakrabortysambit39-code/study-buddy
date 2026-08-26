from datetime import date, timedelta

from services.database import connection


def ensure_v7_tables():
    with connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS focus_sessions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            minutes INTEGER NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS achievements (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            achievement_key TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, achievement_key)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS focus_user_idx ON focus_sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS achievements_user_idx ON achievements(user_id)")


def focus_summary(user_id):
    with connection() as conn:
        row = conn.execute("SELECT COALESCE(SUM(minutes) FILTER (WHERE completed),0) AS minutes, COUNT(*) FILTER (WHERE completed) AS sessions FROM focus_sessions WHERE user_id=%s", (user_id,)).fetchone()
    return {"minutes": row["minutes"] or 0, "sessions": row["sessions"] or 0}


def save_focus(user_id, minutes):
    with connection() as conn:
        conn.execute("INSERT INTO focus_sessions (user_id, minutes, completed) VALUES (%s,%s,TRUE)", (user_id, minutes))


def subject_analytics(user_id):
    with connection() as conn:
        rows = conn.execute("""SELECT COALESCE(NULLIF(kind, ''), 'other') AS kind,
            COALESCE(SUM(score),0) AS score, COALESCE(SUM(total),0) AS total,
            COUNT(*) AS attempts
            FROM activity WHERE user_id=%s GROUP BY kind ORDER BY attempts DESC""", (user_id,)).fetchall()
    return [{"subject": r["kind"].replace("_", " ").title(), "score": r["score"], "total": r["total"], "attempts": r["attempts"], "accuracy": round(r["score"] / r["total"] * 100) if r["total"] else 0} for r in rows]


def achievement_list(user_id):
    with connection() as conn:
        return conn.execute("SELECT achievement_key, title, description, xp, unlocked_at FROM achievements WHERE user_id=%s ORDER BY unlocked_at DESC", (user_id,)).fetchall()


def unlock_achievements(user_id, stats_data, notes_count=0, focus_minutes=0):
    candidates = []
    if stats_data["quizzes"] >= 1:
        candidates.append(("first_quiz", "First Quiz", "Complete your first quiz.", 20))
    if stats_data["quizzes"] >= 10:
        candidates.append(("quiz_10", "Quiz Rookie", "Complete 10 quizzes.", 50))
    if stats_data["accuracy"] >= 100 and stats_data["quizzes"] >= 1:
        candidates.append(("perfect", "Perfect Score", "Reach 100% quiz accuracy.", 50))
    if stats_data["xp"] >= 100:
        candidates.append(("xp_100", "100 XP", "Earn your first 100 XP.", 25))
    if stats_data["streak"] >= 7:
        candidates.append(("streak_7", "7 Day Streak", "Study for seven consecutive days.", 75))
    if notes_count >= 10:
        candidates.append(("notes_10", "Note Maker", "Save 10 study notes.", 50))
    if focus_minutes >= 120:
        candidates.append(("focus_120", "Focus Mode", "Complete 120 focused study minutes.", 50))
    with connection() as conn:
        for key, title, description, xp in candidates:
            conn.execute("INSERT INTO achievements (user_id, achievement_key, title, description, xp) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (user_id, achievement_key) DO NOTHING", (user_id, key, title, description, xp))
    return achievement_list(user_id)
