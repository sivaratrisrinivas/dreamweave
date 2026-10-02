import os

bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = 4  # threads keep streaming responses from blocking other users
timeout = 120
accesslog = "-"
