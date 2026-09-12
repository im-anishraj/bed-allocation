from app import app
import os

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(debug=True, host=host, port=8888)



