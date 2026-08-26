import json
import os
from io import BytesIO
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, send_file, flash

from app_v5 import app, current_user_id, login_required, grade_options
from services.database import connection, DatabaseNotConfigured
from services.v7 import ensure_v7_tables, focus_summary, save_focus, unlock_achievements, record_quiz_attempt, weak_topics
from services.progress import record, stats
from services.notes import list_notes
from services.groq_ai import ai
from services.quiz_generator import quiz_generator


if os.getenv("DATABASE_URL"):
    ensure_v7_tables()


def v7_user():
    return current_user_id()


def notes_search(user_id, query=""):
    with connection() as conn:
        if query:
            q = f"%{query}%"
            return conn.execute("SELECT id,title,subject,content,created_at FROM notes WHERE user_id=%s AND (title ILIKE %s OR subject ILIKE %s OR content ILIKE %s) ORDER BY created_at DESC", (user_id, q, q, q)).fetchall()
        return conn.execute("SELECT id,title,subject,content,created_at FROM notes WHERE user_id=%s ORDER BY created_at DESC", (user_id,)).fetchall()


def planner_tasks(user_id):
    with connection() as conn:
        return conn.execute("SELECT id,task_date,subject,topic,minutes,action,completed FROM study_tasks WHERE user_id=%s ORDER BY task_date,id", (user_id,)).fetchall()


def smart_reminders(user_stats, tasks):
    reminders = []
    if user_stats["streak"] == 0: reminders.append("Start a study session today to build your streak.")
    if user_stats["quizzes"] == 0: reminders.append("Try your first quiz to start measuring your progress.")
    if user_stats["accuracy"] and user_stats["accuracy"] < 70: reminders.append("Your quiz accuracy is below 70%. Review your notes before your next quiz.")
    incomplete = [t for t in tasks if not t["completed"]]
    if incomplete: reminders.append(f"You have {len(incomplete)} unfinished study task(s) in your planner.")
    return reminders


def generate_study_plan(grade, subjects, exam_date, daily_minutes, goal):
    client = ai._get_client()
    if not client: return None, "Groq AI is not configured yet."
    schema = {"type":"object","properties":{"plan":{"type":"array","items":{"type":"object","properties":{"day":{"type":"integer"},"subject":{"type":"string"},"topic":{"type":"string"},"minutes":{"type":"integer"},"action":{"type":"string"}},"required":["day","subject","topic","minutes","action"],"additionalProperties":False}}},"required":["plan"],"additionalProperties":False}
    prompt = f"Create a practical 7-day study plan for Grade {grade}. Subjects: {subjects}. Exam date: {exam_date}. Maximum daily study time: {daily_minutes} minutes. Goal: {goal}. Balance learning, revision, practice and self-testing. Keep each day within the time limit. Return exactly 7 days and only JSON matching the schema."
    try:
        response = client.chat.completions.create(model=ai.model, messages=[{"role":"system","content":"You are Study Buddy's expert study planner."},{"role":"user","content":prompt}], response_format={"type":"json_schema","json_schema":{"name":"study_plan","strict":True,"schema":schema}}, temperature=0.3, max_completion_tokens=1800)
        data = json.loads(response.choices[0].message.content or "{}")
        if len(data.get("plan", [])) != 7: return None, "The AI did not return a complete 7-day plan. Please try again."
        return data, None
    except Exception as exc:
        print(f"Study plan generation error: {exc}")
        return None, "I couldn't generate the study plan right now. Please try again."


# Use a unique endpoint because app_v5 already owns /planner.
@app.route("/planner", methods=["GET", "POST"], endpoint="planner_v7")
@login_required
def planner():
    uid = v7_user(); error = None; plan = None
    form = {"grade": request.form.get("grade", "7"), "subjects": request.form.get("subjects", "Science, Maths"), "exam_date": request.form.get("exam_date", ""), "daily_minutes": request.form.get("daily_minutes", "60"), "goal": request.form.get("goal", "Prepare for my exams")}
    if request.method == "POST":
        if request.form.get("action") == "save":
            try:
                start = date.fromisoformat(request.form.get("start_date")); raw = json.loads(request.form.get("plan_json", "[]"))
                with connection() as conn:
                    conn.execute("DELETE FROM study_tasks WHERE user_id=%s AND task_date >= %s", (uid, start))
                    for item in raw[:7]: conn.execute("INSERT INTO study_tasks (user_id,task_date,subject,topic,minutes,action) VALUES (%s,%s,%s,%s,%s,%s)", (uid, start + timedelta(days=int(item["day"])-1), item["subject"], item["topic"], max(1,int(item["minutes"])), item["action"]))
                record(uid, "planner", 20); return redirect(url_for("planner_v7"))
            except Exception as exc:
                print(f"Planner save error: {exc}"); error = "Could not save the plan. Please try again."
        elif not form["exam_date"]: error = "Choose an exam date."
        else:
            try: daily = max(15, min(240, int(form["daily_minutes"])))
            except ValueError: daily = 60
            plan, error = generate_study_plan(form["grade"], form["subjects"], form["exam_date"], daily, form["goal"])
    tasks = planner_tasks(uid)
    return render_template("planner_v7.html", form=form, plan=plan, plan_json=json.dumps(plan["plan"]) if plan else "[]", start_date=date.today().isoformat(), tasks=tasks, error=error, grades=grade_options())


@app.route("/planner/complete/<int:task_id>", methods=["POST"])
@login_required
def complete_planner_task(task_id):
    uid = v7_user()
    with connection() as conn:
        task = conn.execute("SELECT completed FROM study_tasks WHERE id=%s AND user_id=%s", (task_id, uid)).fetchone()
        if task and not task["completed"]:
            conn.execute("UPDATE study_tasks SET completed=TRUE WHERE id=%s AND user_id=%s", (task_id, uid)); record(uid, "planner_task", 15)
    return redirect(url_for("planner_v7"))


@app.route("/focus", methods=["GET", "POST"])
@login_required
def focus():
    uid = v7_user(); message = None
    if request.method == "POST":
        try: minutes = max(1, min(180, int(request.form.get("minutes", "25"))))
        except ValueError: minutes = 25
        save_focus(uid, minutes); record(uid, "focus", minutes // 5 + 5); message = f"Great work! {minutes} focused minutes added to your progress."
    return render_template("focus.html", summary=focus_summary(uid), message=message)


@app.route("/analytics")
@login_required
def analytics():
    uid = v7_user(); user_stats = stats(uid); focus_data = focus_summary(uid); tasks = planner_tasks(uid)
    with connection() as conn: subject_rows = conn.execute("SELECT subject, COUNT(*) AS notes FROM notes WHERE user_id=%s GROUP BY subject ORDER BY notes DESC", (uid,)).fetchall()
    achievements = unlock_achievements(uid, user_stats, len(list_notes(uid)), focus_data["minutes"])
    return render_template("analytics.html", stats=user_stats, focus=focus_data, subjects=subject_rows, achievements=achievements, reminders=smart_reminders(user_stats, tasks), weak=weak_topics(uid))


@app.route("/achievements")
@login_required
def achievements():
    uid = v7_user(); user_stats = stats(uid); focus_data = focus_summary(uid)
    return render_template("achievements.html", achievements=unlock_achievements(uid, user_stats, len(list_notes(uid)), focus_data["minutes"]))


@app.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip(); return render_template("search.html", query=query, results=notes_search(v7_user(), query))


@app.route("/worksheet", methods=["GET", "POST"])
def worksheet():
    form = {"grade": request.form.get("grade", "7"), "subject": request.form.get("subject", "Science"), "topic": request.form.get("topic", ""), "difficulty": request.form.get("difficulty", "medium"), "count": request.form.get("count", "10")}; questions = None; error = None
    if request.method == "POST":
        if not form["topic"].strip(): error = "Enter a topic first."
        else:
            try: count = max(3, min(20, int(form["count"])))
            except ValueError: count = 10
            data, error = quiz_generator.generate(form["grade"], form["subject"], form["topic"], form["difficulty"], count)
            if data: questions = data.get("questions", [])
    return render_template("worksheet.html", form=form, questions=questions, error=error, grades=grade_options())


@app.route("/export/note/<int:note_id>")
@login_required
def export_note(note_id):
    with connection() as conn: note = conn.execute("SELECT title,subject,content FROM notes WHERE id=%s AND user_id=%s", (note_id, v7_user())).fetchone()
    if not note: return redirect(url_for("notes"))
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from xml.sax.saxutils import escape
    except ImportError:
        flash("PDF export is temporarily unavailable. Please redeploy after installing the PDF dependency.", "error"); return redirect(url_for("notes"))
    output = BytesIO(); doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45); styles = getSampleStyleSheet()
    story = [Paragraph(escape(note["title"]), styles["Title"]), Paragraph(escape(note["subject"]), styles["Heading2"]), Spacer(1, 12)]
    for block in note["content"].split("\n"):
        if block.strip(): story += [Paragraph(escape(block), styles["BodyText"]), Spacer(1, 7)]
    doc.build(story); output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{note['title'].replace(' ', '_')}.pdf", mimetype="application/pdf")


@app.route("/api/voice-tutor", methods=["POST"])
def voice_tutor():
    data = request.get_json(silent=True) or {}; prompt = (data.get("prompt") or "").strip()
    if not prompt: return {"answer": "Please say a question first."}, 400
    return {"answer": ai.ask(prompt)}


@app.after_request
def capture_quiz_attempt(response):
    try:
        uid = current_user_id()
        if uid and request.method == "POST" and request.endpoint in {"results", "ai_quiz_results"}:
            total = int(request.form.get("total", "0")) if request.endpoint == "ai_quiz_results" else 3
            score = int(request.form.get("score", "0")) if request.form.get("score") else None
            if score is None:
                if request.endpoint == "ai_quiz_results":
                    total = max(1, total); score = sum(request.form.get(f"q{i}") == request.form.get(f"answer{i}") for i in range(total))
                else:
                    subject = request.view_args.get("subject", "General") if request.view_args else "General"
                    answers = [request.form.get(f"q{i}") for i in range(total)]
                    score = sum(1 for a in answers if a)
            subject = request.form.get("subject") or (request.view_args.get("subject", "General") if request.view_args else "General")
            topic = request.form.get("topic") or subject
            record_quiz_attempt(uid, subject, topic, score, total)
    except Exception as exc:
        print(f"V7 quiz tracking error: {exc}")
    return response


@app.context_processor
def v7_context(): return {"v7_enabled": True}


@app.errorhandler(DatabaseNotConfigured)
def v7_database_error(_error): return render_template("database_error.html"), 503
