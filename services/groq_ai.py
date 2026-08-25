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
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=0.4,
                max_completion_tokens=700,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"Groq API error: {exc}")
            return "I couldn't reach the AI service right now. Please check the Groq API key and Render logs."

    def generate_notes(self, grade, subject, topic, detail="medium"):
        client = self._get_client()
        if not client:
            return None, "Groq AI is not configured yet."
        schema = {
            "type": "object",
            "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
            "required": ["title", "content"],
            "additionalProperties": False,
        }
        prompt = f"""Create clear school study notes for Grade {grade}.
Subject: {subject}
Topic: {topic}
Detail level: {detail}

Use simple, age-appropriate language. Include a short overview, key concepts, important facts, examples where useful, and a quick revision section. Use readable headings and bullet points. Do not invent facts. Return only the note title and note content."""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Study Buddy's expert school-notes generator."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_schema", "json_schema": {"name": "study_notes", "strict": True, "schema": schema}},
                temperature=0.4,
                max_completion_tokens=2500,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            if not data.get("title") or not data.get("content"):
                return None, "The AI returned an empty note. Please try again."
            return data, None
        except Exception as exc:
            print(f"Groq notes generation error: {exc}")
            return None, "I couldn't generate the notes right now. Please try again."


ai = GroqAI()
