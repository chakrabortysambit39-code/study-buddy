import json
from datetime import date, timedelta

from services.database import connection
from services.groq_ai import ai


def generate_plan(grade, subjects, exam_date, daily_minutes, goal, days=7):
    subject_text = ", ".join(subjects)
    prompt = f"""Create a practical {days}-day study plan for a Grade {grade} student.
Subjects: {subject_text}
Exam date: {exam_date}
Daily study time: {daily_minutes} minutes
Goal: {goal}

Make every day realistic. Mix learning, revision, practice, and self-testing. Keep each day's total minutes at or below the student's daily limit. Return exactly {days} tasks, one for each day, numbered 1 to {days}. Use age-appropriate language."""
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "integer"},
                        "subject": {"type": "string"},
                        "topic": {"type": "string"},
                        "minutes": {"type": "integer"},
                        "action": {"type": "string"},
                    },
                    "required": ["day", "subject", "topic", "minutes", "action"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "tasks"],
        "additionalProperties": False,
    }
    client = ai._get_client()
    if not client:
        return None, "Groq AI is not configured yet."
    try:
        response = client.chat.completions.create(
            model=ai.model,
            messages=[
                {"role": "system", "content": "You are Study Buddy's expert study-planning coach. Make plans realistic, focused, and encouraging."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "study_plan", "strict": True, "schema": schema}},
            temperature=0.4,
            max_completion_tokens=2500,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        tasks = data.get("tasks", [])
        if len(tasks) != days:
            return None, "The AI returned an incomplete study plan. Please try again."
        return data, None
    except Exception as exc:
        print(f"Planner generation error: {exc}")
        return None, "I couldn't generate the study plan right now. Please try again."


def save_plan(user_id, plan_title, exam_date, tasks):
    start = date.today()
    with connection() as conn:
        conn.execute("DELETE FROM study_tasks WHERE user_id = %s", (user_id,))
        for task in tasks:
            task_day = max(1, int(task.get("day", 1)))
            task_date = start + timedelta(days=task_day - 1)
            conn.execute(
                "INSERT INTO study_tasks (user_id, task_date, subject, topic, minutes, action) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, task_date, task.get("subject", "General"), task.get("topic", "Revision"), int(task.get("minutes", 20)), task.get("action", "Study and review")),
            )
    return True


def list_tasks(user_id):
    with connection() as conn:
        return conn.execute("SELECT id, task_date, subject, topic, minutes, action, completed FROM study_tasks WHERE user_id = %s ORDER BY task_date, id", (user_id,)).fetchall()


def complete_task(user_id, task_id):
    with connection() as conn:
        conn.execute("UPDATE study_tasks SET completed = TRUE WHERE id = %s AND user_id = %s", (task_id, user_id))
