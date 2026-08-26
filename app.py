# Production entrypoint for Render.
# V7 extends the stable V5 app with focus mode, analytics, achievements,
# worksheets, search, PDF export, and voice-tutor support.
from app_v7 import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
