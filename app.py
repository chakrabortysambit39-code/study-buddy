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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
