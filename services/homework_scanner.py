import base64
import json
import os

from groq import Groq


HOMEWORK_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "detected_text": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "answer", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "detected_text", "items"],
    "additionalProperties": False,
}


class HomeworkScanner:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def scan(self, image_bytes, mime_type, grade, subject):
        if not self.client:
            return None, "Groq AI is not configured. Add GROQ_API_KEY in Render Environment Variables."

        if len(image_bytes) > 20 * 1024 * 1024:
            return None, "That image is larger than 20 MB. Please upload a smaller image."

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:{mime_type};base64,{encoded}"
        prompt = f"""Read this homework image carefully.
Student grade: {grade}
Subject: {subject}

Tasks:
1. Transcribe the visible homework questions as accurately as possible.
2. Identify each distinct question or exercise.
3. Give a helpful answer for each question.
4. Give a short, student-friendly explanation for each answer.
5. Do not invent questions that are not visible.
6. If something is unreadable, say so clearly instead of guessing.

Return the result using the requested JSON structure."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Study Buddy's homework scanner. You combine careful OCR with accurate, grade-appropriate tutoring.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_completion_tokens=5000,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            if not isinstance(data.get("items"), list):
                return None, "The AI could not read the homework in a usable format. Please try a clearer image."
            return data, None
        except Exception as exc:
            print(f"Homework scan error: {type(exc).__name__}: {exc}")
            return None, "I couldn't read that homework image right now. Please try a clearer image."


homework_scanner = HomeworkScanner()
