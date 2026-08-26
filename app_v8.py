from flask import render_template, request, jsonify
from app_v7 import app
from services.groq_ai import ai


@app.route("/ai-face", methods=["GET"])
def ai_face_tutor():
    return render_template("ai_face.html")


@app.route("/api/ai-face/teach", methods=["POST"])
def ai_face_teach():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    grade = (data.get("grade") or "7").strip()
    subject = (data.get("subject") or "Science").strip()
    topic = (data.get("topic") or "").strip()
    if not prompt and not topic:
        return jsonify({"error": "Tell me what you want to learn."}), 400
    learner_request = prompt or f"Teach me {topic}."
    system = (
        f"You are Study Buddy's friendly AI teacher teaching Grade {grade} {subject}. "
        "Teach like a real classroom teacher: use short spoken paragraphs, simple examples, and occasional check-for-understanding questions. "
        "Do not use markdown tables or long walls of text because your response will be spoken aloud. "
        "Keep the first explanation under about 180 words unless the learner explicitly asks for more detail. "
        "Be encouraging but do not give empty praise."
    )
    client = ai._get_client()
    if not client:
        return jsonify({"error": "Groq AI is not configured yet."}), 503
    try:
        response = client.chat.completions.create(
            model=ai.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": learner_request}],
            temperature=0.5,
            max_completion_tokens=500,
        )
        answer = (response.choices[0].message.content or "").strip()
        return jsonify({"answer": answer, "grade": grade, "subject": subject})
    except Exception as exc:
        print(f"AI face tutor error: {exc}")
        return jsonify({"error": "I couldn't prepare the lesson right now. Please try again."}), 500


@app.route("/api/ai-face/lesson", methods=["POST"])
def ai_face_lesson():
    data = request.get_json(silent=True) or {}
    grade = (data.get("grade") or "7").strip()
    subject = (data.get("subject") or "Science").strip()
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Enter a topic first."}), 400
    return ai_face_teach_proxy(grade, subject, f"Start a mini lesson on {topic}. Explain the idea simply, give one everyday example, then ask me one short question to check my understanding.")


def ai_face_teach_proxy(grade, subject, prompt):
    client = ai._get_client()
    if not client:
        return jsonify({"error": "Groq AI is not configured yet."}), 503
    try:
        response = client.chat.completions.create(
            model=ai.model,
            messages=[
                {"role": "system", "content": f"You are a warm Grade {grade} {subject} teacher. This is a spoken mini-lesson. Use natural speech, short paragraphs, one simple example, and finish with one question for the student. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_completion_tokens=500,
        )
        return jsonify({"answer": (response.choices[0].message.content or "").strip()})
    except Exception as exc:
        print(f"AI face lesson error: {exc}")
        return jsonify({"error": "I couldn't start the lesson right now. Please try again."}), 500
