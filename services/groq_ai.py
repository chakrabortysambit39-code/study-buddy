import os

from groq import Groq


class GroqAI:
    def __init__(self):
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
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
                max_tokens=700,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            print(f"Groq API error: {exc}")
            return "I couldn't reach the AI service right now. Please check the Groq API key and Render logs."


ai = GroqAI()
