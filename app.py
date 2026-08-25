from flask import Flask, render_template, request, redirect, url_for

from services.groq_ai import ai
from services.quiz_generator import quiz_generator
from services.homework_scanner import homework_scanner
from services.notes import list_notes, create_note, delete_note

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

QUESTIONS = {
    "maths": [
        {"question": "What is 7 × 8?", "options": ["54", "56", "64", "48"], "answer": "56"},
        {"question": "What is 144 ÷ 12?", "options": ["10", "11", "12", "14"], "answer": "12"},
        {"question": "What is 25 + 37?", "options": ["52", "62", "72", "57"], "answer": "62"},
    ],
    "science": [
        {"question": "Which planet is known as the Red Planet?", "options": ["Earth", "Mars", "Jupiter", "Venus"], "answer": "Mars"},
        {"question": "What gas do humans need to breathe?", "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], "answer": "Oxygen"},
        {"question": "What is the process by which plants make food?", "options": ["Respiration", "Digestion", "Photosynthesis", "Evaporation"], "answer": "Photosynthesis"},
    ],
    "english": [
        {"question": "Which word is a noun?", "options": ["Quickly", "Beautiful", "School", "Run"], "answer": "School"},
        {"question": "What is the plural of 'child'?", "options": ["Childs", "Children", "Childes", "Childrens"], "answer": "Children"},
        {"question": "Choose the correct verb: She ___ to school every day.", "options": ["go", "goes", "going", "gone"], "answer": "goes"},
    ],
    "french": [
        {"question": "What does 'bonjour' mean?", "options": ["Goodbye", "Hello", "Thank you", "Please"], "answer": "Hello"},
        {"question": "What is 'book' in French?", "options": ["livre", "maison", "chien", "école"], "answer": "livre"},
        {"question": "Which means 'thank you'?", "options": ["Salut", "Merci", "Bonsoir", "Pardon"], "answer": "Merci"},
    ],
}

SUBJECTS = {
    "maths": {"name": "Maths", "emoji": "📐"},
    "science": {"name": "Science", "emoji": "🔬"},
    "english": {"name": "English", "emoji": "📖"},
    "french": {"name": "French", "emoji": "🇫🇷"},
}


def grade_options():
    return [str(i) for i in range(1, 13)]


@app.route("/")
def home():
    return render_template("index.html", subjects=SUBJECTS)


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
    for index, question in enumerate(questions):
        selected = request.form.get(f"q{index}")
        correct = selected == question["answer"]
        if correct:
            score += 1
        results_data.append({**question, "selected": selected, "correct": correct})
    percentage = round((score / len(questions)) * 100) if questions else 0
    return render_template("results.html", subject=SUBJECTS[subject], score=score, total=len(questions), percentage=percentage, results=results_data)


@app.route("/ai", methods=["GET", "POST"])
def ai_tutor():
    answer = None
    prompt = ""
    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        if prompt:
            answer = ai.ask(prompt)
    return render_template("ai.html", answer=answer, prompt=prompt)


@app.route("/generate-quiz", methods=["GET", "POST"])
def generate_quiz():
    form = {
        "grade": request.form.get("grade", "7").strip(),
        "subject": request.form.get("subject", "Science").strip(),
        "topic": request.form.get("topic", "").strip(),
        "difficulty": request.form.get("difficulty", "medium").lower(),
        "count": request.form.get("count", "5"),
    }
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
            quiz_data, error = quiz_generator.generate(form["grade"], form["subject"], form["topic"], form["difficulty"], count)
            if quiz_data:
                questions = quiz_data.get("questions", [])
    return render_template("generate_quiz.html", form=form, questions=questions, error=error, grades=grade_options())


@app.route("/ai-quiz-results", methods=["POST"])
def ai_quiz_results():
    total = max(1, int(request.form.get("total", "1")))
    score = 0
    results_data = []
    for index in range(total):
        selected = request.form.get(f"q{index}")
        answer = request.form.get(f"answer{index}")
        correct = selected == answer
        if correct:
            score += 1
        results_data.append({"selected": selected, "answer": answer, "correct": correct})
    percentage = round(score / total * 100)
    subject = request.form.get("subject", "AI Quiz")
    grade = request.form.get("grade", "")
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
    quiz_data, error = quiz_generator.generate_from_source(grade, subject, source_text, 5)
    questions = quiz_data.get("questions", []) if quiz_data else None
    form = {"grade": grade, "subject": subject, "topic": "Homework", "difficulty": "medium", "count": "5"}
    return render_template("generate_quiz.html", form=form, questions=questions, error=error, grades=grade_options())


@app.route("/notes", methods=["GET", "POST"])
def notes():
    note = None
    error = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "General").strip() or "General"
        content = request.form.get("content", "").strip()
        if not title or not content:
            error = "Please enter both a title and some notes."
        else:
            create_note(title, subject, content)
            return redirect(url_for("notes"))
    return render_template("notes.html", notes=list_notes(), note=note, error=error)


@app.route("/notes/delete/<int:note_id>", methods=["POST"])
def delete_note_route(note_id):
    delete_note(note_id)
    return redirect(url_for("notes"))


@app.errorhandler(413)
def too_large(_error):
    return render_template("homework.html", form={"grade": "7", "subject": "Science"}, result=None, error="That image is too large. Please upload an image under 15 MB.", grades=grade_options()), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
