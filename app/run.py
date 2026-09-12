import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from bootstrap_data import ensure_data_artefacts

# Automatically prepare data artefacts if missing
ensure_data_artefacts(root=ROOT_DIR)

from app import app

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(debug=True, host=host, port=8888)
