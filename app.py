# Production entrypoint for Render.
# V5 lives in app_v5.py; this compatibility entrypoint keeps
# Render's existing `gunicorn app:app` command working.
from app_v5 import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
