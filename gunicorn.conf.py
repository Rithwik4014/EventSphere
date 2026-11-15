# gunicorn.conf.py
"""
Gunicorn configuration for EventSphere production deployment on Render.
"""

import os

# Dynamic port binding for Render ($PORT)
port = os.environ.get("PORT", "5050")
bind = f"0.0.0.0:{port}"

# Concurrency and worker settings
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("PYTHON_THREADS", 2))
worker_class = "gthread"
timeout = int(os.environ.get("WEB_TIMEOUT", 120))
keepalive = 5

# Logging to standard output/error for Render log stream
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
capture_output = True
