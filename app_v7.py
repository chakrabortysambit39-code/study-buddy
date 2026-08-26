import os
from io import BytesIO
from datetime import date

from flask import render_template, request, redirect, url_for, session, send_file, flash

from app_v5 import app, current_user_id, login_required, grade_options
from services.database import connection, DatabaseNotConfigured
from services.v7 import ensure_v7_tables, focus_summary, save_focus, achievement_list, unlock_achievements
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


def smart_reminders(user_id, user_stats, tasks):
    reminders = []
    if user_stats["streak"] == 0:
        reminders.append("Start a study session today to build your streak.")
    if user_stats["quizzes"] == 0:
        reminders.append("Try your first quiz to start measuring your progress.")
    if user_stats["accuracy"] and user_stats["accuracy"] < 70:
        reminders.append("Your quiz accuracy is below 70%. Review your notes before your next quiz.")
    incomplete = [t for t in tasks if not t["completed"]]
    if incomplete:
        reminders.append(f"You have {len(incomplete)} unfinished study task(s) in your planner.")
    return reminders


@app.route("/focus", methods=["GET", "POST"])
@login_required
def focus():
    uid = v7_user()
    message = None
    if request.method == "POST":
        try:
            minutes = max(1, min(180, int(request.form.get("minutes", "25"))))
        except ValueError:
            minutes = 25
        save_focus(uid, minutes)
        record(uid, "focus", minutes // 5 + 5)
        message = f"Great work! {minutes} focused minutes added to your progress."
    return render_template("focus.html", summary=focus_summary(uid), message=message)


@app.route("/analytics")
@login_required
def analytics():
    uid = v7_user()
    user_stats = stats(uid)
    focus_data = focus_summary(uid)
    with connection() as conn:
        subject_rows = conn.execute("SELECT subject, COUNT(*) AS notes FROM notes WHERE user_id=%s GROUP BY subject ORDER BY notes DESC", (uid,)).fetchall()
    achievements = unlock_achievements(uid, user_stats, len(list_notes(uid)), focus_data["minutes"])
    return render_template("analytics.html", stats=user_stats, focus=focus_data, subjects=subject_rows, achievements=achievements)


@app.route("/achievements")
@login_required
def achievements():
    uid = v7_user()
    user_stats = stats(uid)
    focus_data = focus_summary(uid)
    items = unlock_achievements(uid, user_stats, len(list_notes(uid)), focus_data["minutes"])
    return render_template("achievements.html", achievements=items)


@app.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    results = notes_search(v7_user(), query)
    return render_template("search.html", query=query, results=results)


@app.route("/worksheet", methods=["GET", "POST"])
def worksheet():
    form = {"grade": request.form.get("grade", "7"), "subject": request.form.get("subject", "Science"), "topic": request.form.get("topic", ""), "difficulty": request.form.get("difficulty", "medium"), "count": request.form.get("count", "10")}
    questions = None
    error = None
    if request.method == "POST":
        if not form["topic"].strip():
            error = "Enter a topic first."
        else:
            try:
                count = max(3, min(20, int(form["count"])))
            except ValueError:
                count = 10
            data, error = quiz_generator.generate(form["grade"], form["subject"], form["topic"], form["difficulty"], count)
            if data:
                questions = data.get("questions", [])
    return render_template("worksheet.html", form=form, questions=questions, error=error, grades=grade_options())


@app.route("/export/note/<int:note_id>")
@login_required
def export_note(note_id):
    with connection() as conn:
        note = conn.execute("SELECT title,subject,content FROM notes WHERE id=%s AND user_id=%s", (note_id, v7_user())).fetchone()
    if not note:
        return redirect(url_for("notes"))
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from xml.sax.saxutils import escape
    except ImportError:
        flash("PDF export is temporarily unavailable. Please redeploy after installing the PDF dependency.", "error")
        return redirect(url_for("notes"))
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(note["title"]), styles["Title"]), Paragraph(escape(note["subject"]), styles["Heading2"]), Spacer(1, 12)]
    for block in note["content"].split("\n"):
        if block.strip():
            story.append(Paragraph(escape(block), styles["BodyText"]))
            story.append(Spacer(1, 7))
    doc.build(story)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"{note['title'].replace(' ', '_')}.pdf", mimetype="application/pdf")


@app.route("/api/voice-tutor", methods=["POST"])
def voice_tutor():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return {"answer": "Please say a question first."}, 400
    return {"answer": ai.ask(prompt)}


@app.context_processor
def v7_context():
    return {"v7_enabled": True}


# V7 error page remains usable if PostgreSQL is temporarily unavailable.
@app.errorhandler(DatabaseNotConfigured)
def v7_database_error(_error):
    return render_template("database_error.html"), 503
