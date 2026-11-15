# run.py
"""
Application entry point for EventSphere.
"""

import os
from app import create_app

flask_env = os.environ.get("FLASK_ENV") or ("production" if os.environ.get("RENDER") else "development")
app = create_app(flask_env)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, use_reloader=False)
