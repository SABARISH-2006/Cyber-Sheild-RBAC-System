import os
import sys

# Ensure parent directory is in search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend_flask.app import create_app
from backend_flask.config import Config

app = create_app(Config)

if __name__ == "__main__":
    # Spins up the Flask server on local port 5000
    print("=" * 60)
    print("STARTING CYBER-SHIELD FLASK BACKEND SERVER")
    print("URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
