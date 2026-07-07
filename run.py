"""Entry point: python -m app.web"""

from app.web import run_server

if __name__ == "__main__":
    run_server(open_browser=True)
