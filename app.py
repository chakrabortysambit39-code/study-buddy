from flask import Flask, render_template, request, redirect, url_for

from services.groq_ai import ai

app = Flask(__name__)

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
    return render_template(
        "results.html",
        subject=SUBJECTS[subject],
        score=score,
        total=len(questions),
        percentage=percentage,
        results=results_data,
    )


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
    questions = None
    error = None
    form = {"subject": "Maths", "topic": "", "difficulty": "medium", "count": "5"}

    if request.method == "POST":
        form["subject"] = request.form.get("subject", "Maths").strip()
        form["topic"] = request.form.get("topic", "").strip()
        form["difficulty"] = request.form.get("difficulty", "medium").strip().lower()
        try:
            form["count"] = str(max(3, min(10, int(request.form.get("count", "5")))))
        except ValueError:
            form["count"] = "5"

        questions, error = ai.generate_quiz(
            form["subject"], form["topic"], form["difficulty"], int(form["count"])
        )

    return render_template("generate_quiz.html", questions=questions, error=error, form=form)


@app.route("/ai-quiz-results", methods=["POST"])
def ai_quiz_results():
    try:
        total = int(request.form.get("total", "0"))
    except ValueError:
        total = 0

    score = 0
    results_data = []
    for index in range(total):
        selected = request.form.get(f"q{index}")
        answer = request.form.get(f"answer{index}")
        correct = selected == answer
        score += int(correct)
        results_data.append({"selected": selected, "answer": answer, "correct": correct})

    percentage = round((score / total) * 100) if total else 0
    return render_template(
        "ai_quiz_results.html",
        subject=request.form.get("subject", "AI Quiz"),
        score=score,
        total=total,
        percentage=percentage,
        results=results_data,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
