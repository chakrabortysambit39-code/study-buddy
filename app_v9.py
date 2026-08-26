import json
from flask import render_template, request, jsonify
from app_v8 import app
from services.groq_ai import ai


def _adaptive_call(grade, subject, topic, instruction):
    client = ai._get_client()
    if not client:
        return None, "Groq AI is not configured yet."
    system = (
        f"You are Study Buddy's adaptive teacher for Grade {grade} {subject}. "
        f"The topic is {topic}. Adapt to the student's level. Be concise, clear and encouraging. "
        "Never use markdown tables. Give one idea at a time. "
        "When checking an answer, explain the mistake briefly and then give a similar question."
    )
    try:
        response = client.chat.completions.create(
            model=ai.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": instruction}],
            temperature=0.45,
            max_completion_tokens=700,
        )
        return (response.choices[0].message.content or "").strip(), None
    except Exception as exc:
        print(f"Adaptive tutor error: {exc}")
        return None, "I couldn't prepare the adaptive lesson right now. Please try again."


@app.route("/adaptive", methods=["GET"], endpoint="adaptive_room_v9")
def adaptive_room():
    return render_template("adaptive.html")


@app.route("/api/adaptive/start", methods=["POST"], endpoint="adaptive_start_v9")
def adaptive_start():
    data = request.get_json(silent=True) or {}
    grade = str(data.get("grade") or "7").strip()
    subject = str(data.get("subject") or "Science").strip()
    topic = str(data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Enter a topic first."}), 400
    prompt = (
        "Build a 5-step adaptive mini lesson. Return ONLY JSON with keys: "
        "title, level, steps. steps must contain exactly 5 objects with keys "
        "type, heading, content, question. type must be explain, example, check, practice, recap. "
        "The first step should teach the core idea simply. The check should be easy enough to establish the student's starting level. "
        "Keep each content field under 70 words and each question under 25 words."
    )
    text, error = _adaptive_call(grade, subject, topic, prompt)
    if error:
        return jsonify({"error": error}), 503
    try:
        data = json.loads(text)
        if not isinstance(data.get("steps"), list) or len(data["steps"]) != 5:
            raise ValueError("invalid lesson")
        return jsonify(data)
    except Exception:
        return jsonify({"title": f"{topic} — Adaptive Lesson", "level": "Starter", "steps": [
            {"type": "explain", "heading": "Core idea", "content": text, "question": "What is the main idea?"},
            {"type": "example", "heading": "Example", "content": "Let's use a simple example together.", "question": "Can you explain the example in your own words?"},
            {"type": "check", "heading": "Check", "content": "Now let's see what you understand.", "question": "What would happen next?"},
            {"type": "practice", "heading": "Practice", "content": "Try one similar problem.", "question": "What is your answer?"},
            {"type": "recap", "heading": "Quick recap", "content": "Tell me the most important thing you learned.", "question": "What should you remember for your exam?"}
        ]})


@app.route("/api/adaptive/respond", methods=["POST"], endpoint="adaptive_respond_v9")
def adaptive_respond():
    data = request.get_json(silent=True) or {}
    grade = str(data.get("grade") or "7").strip()
    subject = str(data.get("subject") or "Science").strip()
    topic = str(data.get("topic") or "").strip()
    question = str(data.get("question") or "").strip()
    answer = str(data.get("answer") or "").strip()
    if not question or not answer:
        return jsonify({"error": "I need both the question and your answer."}), 400
    prompt = (
        f"Question: {question}\nStudent answer: {answer}\n\n"
        "Evaluate the answer for this grade level. Return ONLY JSON with keys: correct (boolean), "
        "score (integer 0-100), feedback (under 45 words), next_action (one of 'advance','reteach','practice'), "
        "next_question (under 25 words), teaching_tip (under 35 words)."
    )
    text, error = _adaptive_call(grade, subject, topic, prompt)
    if error:
        return jsonify({"error": error}), 503
    try:
        result = json.loads(text)
        return jsonify(result)
    except Exception:
        return jsonify({"correct": False, "score": 0, "feedback": text, "next_action": "reteach", "next_question": question, "teaching_tip": "Let's break the idea into a smaller step."})
