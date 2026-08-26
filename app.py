# Production entrypoint for Render.
# V8 adds the AI Face Tutor on top of the stable V7 app.
from app_v8 import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
