import json
import os

from groq import Groq


QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "options", "answer", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "questions"],
    "additionalProperties": False,
}


class QuizGenerator:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def _call(self, prompt):
        if not self.client:
            return None, "Groq AI is not configured. Add GROQ_API_KEY in Render Environment Variables."
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Study Buddy's quiz generator. Create accurate, grade-appropriate educational quizzes."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_schema", "json_schema": {"name": "study_buddy_quiz", "strict": True, "schema": QUIZ_SCHEMA}},
                max_completion_tokens=5000,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            questions = data.get("questions", [])
            if len(questions) < 1:
                return None, "The AI did not return any usable questions. Please try again."
            for question in questions:
                options = question.get("options", [])
                if len(options) != 4 or len(set(options)) != 4 or question.get("answer") not in options:
                    return None, "The AI returned an invalid quiz format. Please try again."
            return data, None
        except Exception as exc:
            print(f"Quiz generation error: {type(exc).__name__}: {exc}")
            return None, "I couldn't generate the quiz right now. Please try again."

    def generate(self, grade, subject, topic, difficulty, count):
        count = max(3, min(int(count), 10))
        prompt = f"""Create exactly {count} multiple-choice questions for a Grade {grade} student.
Grade: {grade}
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Rules:
- Match the expected curriculum depth and vocabulary for Grade {grade}.
- Return exactly {count} questions.
- Every question has exactly 4 distinct options.
- The answer exactly matches one option.
- Keep explanations short, accurate, and student-friendly.
- Stay focused on the requested subject and topic."""
        data, error = self._call(prompt)
        if data and len(data.get("questions", [])) != count:
            return None, "The AI returned an unexpected number of questions. Please try again."
        return data, error

    def generate_from_source(self, grade, subject, source_text, count=5):
        count = max(3, min(int(count), 10))
        prompt = f"""Create exactly {count} multiple-choice questions for a Grade {grade} student using ONLY the homework material below.
Grade: {grade}
Subject: {subject}

Homework material:
{source_text[:12000]}

Rules:
- Questions must be based on the supplied homework material.
- Match Grade {grade} level.
- Exactly 4 distinct options per question.
- The answer exactly matches one option.
- Keep explanations short and student-friendly."""
        data, error = self._call(prompt)
        if data and len(data.get("questions", [])) != count:
            return None, "The AI returned an unexpected number of homework questions. Please try again."
        return data, error


quiz_generator = QuizGenerator()
