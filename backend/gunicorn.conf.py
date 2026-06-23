import os

# Bind to the dynamic PORT environment variable set by Render, default to 5000
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Standard production settings
workers = 2
timeout = 120
