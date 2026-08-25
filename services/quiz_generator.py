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
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
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

    def generate(self, subject, topic, difficulty, count):
        if not self.client:
            return None, "Groq AI is not configured. Add GROQ_API_KEY in Render Environment Variables."

        count = max(3, min(int(count), 10))
        prompt = f"""Create a {count}-question multiple-choice quiz for a student.
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Rules:
- Return exactly {count} questions.
- Every question must have exactly 4 distinct options.
- The answer must exactly match one of the four options.
- Explanations should be short, accurate, and student-friendly.
- Stay focused on the requested subject and topic.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Study Buddy's quiz generator. Create accurate educational quizzes appropriate for students.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "study_buddy_quiz",
                        "strict": True,
                        "schema": QUIZ_SCHEMA,
                    },
                },
                max_completion_tokens=5000,
            )

            content = response.choices[0].message.content
            data = json.loads(content or "{}")
            questions = data.get("questions", [])

            if len(questions) != count:
                return None, "The AI returned an unexpected number of questions. Please try again."

            for question in questions:
                options = question.get("options", [])
                answer = question.get("answer")
                if len(options) != 4 or len(set(options)) != 4 or answer not in options:
                    return None, "The AI returned an invalid quiz format. Please try again."

            return data, None

        except Exception as exc:
            print(f"Quiz generation error: {type(exc).__name__}: {exc}")
            return None, "I couldn't generate the quiz right now. Please try again."


quiz_generator = QuizGenerator()
