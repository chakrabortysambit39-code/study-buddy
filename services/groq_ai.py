import json
import os

from groq import Groq


class GroqAI:
    def __init__(self):
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.client = None
        self.api_key = os.getenv("GROQ_API_KEY")

    def _get_client(self):
        if not self.api_key:
            return None
        if self.client is None:
            self.client = Groq(api_key=self.api_key)
        return self.client

    def ask(self, prompt, system="You are Study Buddy, a friendly and accurate AI tutor. Explain things clearly for a student."):
        client = self._get_client()
        if not client:
            return "Groq AI is not configured yet. Add GROQ_API_KEY in Render Environment Variables."

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_completion_tokens=700,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"Groq API error: {exc}")
            return "I couldn't reach the AI service right now. Please check the Groq API key and Render logs."

    def generate_quiz(self, subject, topic, difficulty, count):
        client = self._get_client()
        if not client:
            return None, "Groq AI is not configured yet."

        schema = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 4,
                                "maxItems": 4,
                            },
                            "answer": {"type": "string"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["question", "options", "answer", "explanation"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["questions"],
            "additionalProperties": False,
        }

        prompt = (
            f"Create exactly {count} multiple-choice questions for a student. "
            f"Subject: {subject}. Topic: {topic or 'general ' + subject}. "
            f"Difficulty: {difficulty}. "
            "Each question must have exactly 4 distinct options and exactly one correct answer. "
            "The answer must exactly match one option. Give a short educational explanation. "
            "Avoid trick questions, ambiguity, and unsafe content."
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert school quiz generator. Return only the requested structured quiz.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "study_quiz",
                        "strict": True,
                        "schema": schema,
                    },
                },
                temperature=0.5,
                max_completion_tokens=2500,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            questions = data.get("questions", [])

            if len(questions) != count:
                return None, "The AI returned an unexpected number of questions. Please try again."

            for q in questions:
                if len(q.get("options", [])) != 4 or q.get("answer") not in q.get("options", []):
                    return None, "The AI returned an invalid question. Please try again."

            return questions, None
        except Exception as exc:
            print(f"Groq quiz generation error: {exc}")
            return None, "I couldn't generate the quiz right now. Please try again."


ai = GroqAI()
