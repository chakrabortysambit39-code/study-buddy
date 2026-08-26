# Production entrypoint for Render.
# V8 extends V7 with the interactive AI Face Tutor.
from app_v8 import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
