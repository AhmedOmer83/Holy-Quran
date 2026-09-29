"""Cloud Run entry point; keep one shared experiment cache and analysis lock."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 1
threads = 4
timeout = 300
accesslog = '-'
errorlog = '-'
