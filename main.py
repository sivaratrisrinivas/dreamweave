"""Entry point for gunicorn (`gunicorn main:app`) and `flask --app main run`."""

import logging

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from dreamweave import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(debug=False, port=5000)
