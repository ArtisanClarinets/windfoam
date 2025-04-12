# main.py
"""
Entrypoint script to run the Dash app in debug mode (for local dev).
"""

from app import app

if __name__ == "__main__":
    app.run_server(debug=True)
