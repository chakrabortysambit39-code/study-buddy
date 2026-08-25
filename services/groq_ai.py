import os

from groq import Groq


class GroqAI:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key) if api_key else None
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def ask(self, prompt, system="You are Study Buddy, a friendly and accurate AI tutor. Explain things clearly for a student."):
        if not self.client:
            return "Groq AI is not configured yet. Add GROQ_API_KEY in Render Environment Variables."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()


ai = GroqAI()
