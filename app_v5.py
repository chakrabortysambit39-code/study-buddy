import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg.errors import UniqueViolation

from services.groq_ai import ai
from services.quiz_generator import quiz_generator
from services.homework_scanner import homework_scanner
from services.notes import list_notes, create_note, delete_note
from services.progress import record, stats
from services.database import init_db, DatabaseNotConfigured
from services.planner import generate_plan, save_plan, list_tasks, complete_task

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-this-in-render")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

QUESTIONS = {
    "maths": [{"question": "What is 7 × 8?", "options": ["54", "56", "64", "48"], "answer": "56"}, {"question": "What is 144 ÷ 12?", "options": ["10", "11", "12", "14"], "answer": "12"}, {"question": "What is 25 + 37?", "options": ["52", "62", "72", "57"], "answer": "62"}],
    "science": [{"question": "Which planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Venus"], "answer": "Mars"}, {"question": "What gas do humans need to breathe?", "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], "answer": "Oxygen"}, {"question": "What is the process by which plants make food?", "options": ["Respiration", "Digestion", "Photosynthesis", "Evaporation"], "answer": "Photosynthesis"}],
    "english": [{"question": "Which word is a noun?", "options": ["Quickly", "Beautiful", "School", "Run"], "answer": "School"}, {"question": "What is the plural of 'child'?", "options": ["Childs", "Children", "Childes", "Childrens"], "answer": "Children"}, {"question": "Choose the correct verb: She ___ to school every day.", "options": ["go", "goes", "going", "gone"], "answer": "goes"}],
    "french": [{"question": "What does 'bonjour' mean?", "options": ["Goodbye", "Hello", "Thank you", "Please"], "answer": "Hello"}, {"question": "What is 'book' in French?", "options": ["livre", "maison", "chien", "école"], "answer": "livre"}, {"question": "Which means 'thank you'?", "options": ["Salut", "Merci", "Bonsoir", "Pardon"], "answer": "Merci"}],
}
SUBJECTS = {"maths": {"name": "Maths", "emoji": "📐"}, "science": {"name": "Science", "emoji": "🔬"}, "english": {"name": "English", "emoji": "📖"}, "french": {"name": "French", "emoji": "🇫🇷"}}


def grade_options():
    return [str(i) for i in range(1, 13)]


def current_user_id():
    return session.get("user_id")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            flash("Please log in to access your personal study data.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"logged_in": bool(current_user_id()), "user_name": session.get("user_name")}


@app.route("/")
def home():
    return render_template("index.html", subjects=SUBJECTS)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or "@" not in email or len(password) < 6:
            flash("Enter a name, valid email, and password of at least 6 characters.", "error")
            return render_template("register.html")
        try:
            user = __import__("services.database", fromlist=["create_user"]).create_user(name, email, generate_password_hash(password))
        except UniqueViolation:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")
        except DatabaseNotConfigured:
            flash("Database is not configured on Render yet. Add DATABASE_URL first.", "error")
            return render_template("register.html")
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            from services.database import find_user_by_email
            user = find_user_by_email(email)
        except DatabaseNotConfigured:
            flash("Database is not configured on Render yet. Add DATABASE_URL first.", "error")
            return render_template("login.html")
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(request.args.get("next") or url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    uid = current_user_id()
    user_stats = stats(uid)
    return render_template("dashboard.html", stats=user_stats, notes_count=len(list_notes(uid)), planner_tasks=list_tasks(uid))


@app.route("/quiz/<subject>")
def quiz(subject):
    if subject not in QUESTIONS:
        return redirect(url_for("home"))
    return render_template("quiz.html", subject=SUBJECTS[subject], questions=QUESTIONS[subject], subject_key=subject)


@app.route("/results/<subject>", methods=["POST"])
def results(subject):
    if subject not in QUESTIONS:
        return redirect(url_for("home"))
    questions = QUESTIONS[subject]
    score = 0
    results_data = []
    for i, q in enumerate(questions):
        selected = request.form.get(f"q{i}")
        correct = selected == q["answer"]
        score += int(correct)
        results_data.append({**q, "selected": selected, "correct": correct})
    percentage = round(score / len(questions) * 100) if questions else 0
    if current_user_id():
        record(current_user_id(), "quiz", 10 + score * 5, score, len(questions))
    return render_template("results.html", subject=SUBJECTS[subject], score=score, total=len(questions), percentage=percentage, results=results_data)


@app.route("/ai", methods=["GET", "POST"])
def ai_tutor():
    prompt = request.form.get("prompt", "").strip() if request.method == "POST" else ""
    answer = ai.ask(prompt) if prompt else None
    return render_template("ai.html", answer=answer, prompt=prompt)


@app.route("/generate-quiz", methods=["GET", "POST"])
def generate_quiz():
    form = {"grade": request.form.get("grade", "7").strip(), "subject": request.form.get("subject", "Science").strip(), "topic": request.form.get("topic", "").strip(), "difficulty": request.form.get("difficulty", "medium").lower(), "count": request.form.get("count", "5")}
    questions = None
    error = None
    if request.method == "POST":
        if not form["topic"]:
            error = "Please enter a topic first."
        else:
            try:
                count = int(form["count"])
            except ValueError:
                count = 5
            data, error = quiz_generator.generate(form["grade"], form["subject"], form["topic"], form["difficulty"], count)
            if data:
                questions = data.get("questions", [])
    return render_template("generate_quiz.html", form=form, questions=questions, error=error, grades=grade_options())


@app.route("/ai-quiz-results", methods=["POST"])
def ai_quiz_results():
    total = max(1, int(request.form.get("total", "1")))
    score = 0
    results_data = []
    for i in range(total):
        selected = request.form.get(f"q{i}")
        answer = request.form.get(f"answer{i}")
        correct = selected == answer
        score += int(correct)
        results_data.append({"selected": selected, "answer": answer, "correct": correct})
    percentage = round(score / total * 100)
    subject = request.form.get("subject", "AI Quiz")
    grade = request.form.get("grade", "")
    if current_user_id():
        record(current_user_id(), "ai_quiz", 15 + score * 7, score, total)
    return render_template("ai_quiz_results.html", subject=subject, grade=grade, score=score, total=total, percentage=percentage, results=results_data)


@app.route("/homework", methods=["GET", "POST"])
def homework():
    form = {"grade": request.form.get("grade", "7").strip(), "subject": request.form.get("subject", "Science").strip()}
    result = None
    error = None
    if request.method == "POST":
        image = request.files.get("homework_image")
        if not image or not image.filename:
            error = "Please choose a homework image first."
        elif image.mimetype not in {"image/jpeg", "image/png", "image/webp"}:
            error = "Please upload a JPG, PNG, or WebP image."
        else:
            result, error = homework_scanner.scan(image.read(), image.mimetype, form["grade"], form["subject"])
    return render_template("homework.html", form=form, result=result, error=error, grades=grade_options())


@app.route("/homework-quiz", methods=["POST"])
def homework_quiz():
    source_text = request.form.get("source_text", "").strip()
    grade = request.form.get("grade", "7").strip()
    subject = request.form.get("subject", "General").strip()
    if not source_text:
        return redirect(url_for("homework"))
    data, error = quiz_generator.generate_from_source(grade, subject, source_text, 5)
    questions = data.get("questions", []) if data else None
    form = {"grade": grade, "subject": subject, "topic": "Homework", "difficulty": "medium", "count": "5"}
    return render_template("generate_quiz.html", form=form, questions=questions, error=error, grades=grade_options())


@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    uid = current_user_id()
    error = None
    generated = False
    form = {"grade": request.form.get("grade", "7"), "subject": request.form.get("subject", "Science"), "topic": request.form.get("topic", ""), "detail": request.form.get("detail", "medium"), "title": request.form.get("title", ""), "content": request.form.get("content", "")}
    if request.method == "POST":
        if request.form.get("action", "save") == "generate":
            if not form["topic"].strip():
                error = "Enter a topic to generate notes."
            else:
                data, error = ai.generate_notes(form["grade"], form["subject"], form["topic"], form["detail"])
                if data:
                    form["title"], form["content"], generated = data["title"], data["content"], True
        else:
            title, content, subject = form["title"].strip(), form["content"].strip(), form["subject"].strip() or "General"
            if not title or not content:
                error = "Please enter a title and note content."
            else:
                create_note(uid, title, subject, content)
                record(uid, "note", 10)
                return redirect(url_for("notes"))
    return render_template("notes.html", notes=list_notes(uid), error=error, generated=generated, form=form, grades=grade_options())


@app.route("/notes/delete/<int:note_id>", methods=["POST"])
@login_required
def delete_note_route(note_id):
    delete_note(current_user_id(), note_id)
    return redirect(url_for("notes"))


@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():
    uid = current_user_id()
    error = None
    generated = None
    form = {
        "grade": request.form.get("grade", "7"),
        "subjects": request.form.get("subjects", "Science, Maths"),
        "exam_date": request.form.get("exam_date", ""),
        "daily_minutes": request.form.get("daily_minutes", "60"),
        "goal": request.form.get("goal", "Prepare for my exam"),
    }
    if request.method == "POST" and request.form.get("action") == "generate":
        subjects = [s.strip() for s in form["subjects"].split(",") if s.strip()]
        if not subjects or not form["exam_date"]:
            error = "Enter at least one subject and an exam date."
        else:
            try:
                minutes = max(15, min(240, int(form["daily_minutes"])))
            except ValueError:
                minutes = 60
            generated, error = generate_plan(form["grade"], subjects, form["exam_date"], minutes, form["goal"], 7)
    elif request.method == "POST" and request.form.get("action") == "save":
        tasks_json = request.form.get("tasks_json", "")
        import json
        try:
            tasks = json.loads(tasks_json)
            save_plan(uid, request.form.get("plan_title", "My Study Plan"), request.form.get("exam_date", ""), tasks)
            record(uid, "planner", 15)
            return redirect(url_for("planner"))
        except Exception as exc:
            print(f"Planner save error: {exc}")
            error = "I couldn't save the study plan. Please try again."
    return render_template("planner.html", form=form, generated=generated, error=error, tasks=list_tasks(uid), grades=grade_options())


@app.route("/planner/complete/<int:task_id>", methods=["POST"])
@login_required
def complete_planner_task(task_id):
    complete_task(current_user_id(), task_id)
    record(current_user_id(), "planner_task", 5)
    return redirect(url_for("planner"))


@app.errorhandler(413)
def too_large(_error):
    return render_template("homework.html", form={"grade": "7", "subject": "Science"}, result=None, error="That image is too large. Please upload an image under 15 MB.", grades=grade_options()), 413


@app.errorhandler(DatabaseNotConfigured)
def database_error(_error):
    return render_template("database_error.html"), 503


if os.getenv("DATABASE_URL"):
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
