# Production entrypoint for Render.
# V9 adds the Adaptive Learning Engine on top of the V8 AI Face Tutor.
from app_v9 import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
