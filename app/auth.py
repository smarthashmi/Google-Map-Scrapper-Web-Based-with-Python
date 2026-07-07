"""Password protection for viewing and downloading scraped data."""

import json
from functools import wraps
from pathlib import Path

from flask import redirect, request, session, url_for
from werkzeug.security import check_password_hash

from app.config import AUTH_FILE, DATA_DIR

DEFAULT_EMAIL = "hashmidev21@gmail.com"
# Pre-hashed — plaintext is never stored in source after initial setup
DEFAULT_PASSWORD_HASH = (
    "scrypt:32768:8:1$ZpN2h89p70rrXghC$92365441ad5af8038239760eb1c7798c3784101c50fdcc07cb3edef065ba39c"
    "5038da4201a4def55e36518bfc34a8a07c4db46913e6da36fd076412d812b69c5"
)


def _ensure_auth_file() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if AUTH_FILE.exists():
        return json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    auth = {"email": DEFAULT_EMAIL, "password_hash": DEFAULT_PASSWORD_HASH}
    AUTH_FILE.write_text(json.dumps(auth, indent=2), encoding="utf-8")
    return auth


def verify_login(email: str, password: str) -> bool:
    auth = _ensure_auth_file()
    if email.strip().lower() != auth.get("email", "").strip().lower():
        return False
    return check_password_hash(auth.get("password_hash", ""), password)


def is_authenticated() -> bool:
    return bool(session.get("authenticated"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            next_url = request.path
            if request.query_string:
                next_url += "?" + request.query_string.decode()
            return redirect(url_for("login", next=next_url))
        return view(*args, **kwargs)

    return wrapped


def login_required_api(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            from flask import jsonify
            return jsonify({"ok": False, "error": "Login required"}), 401
        return view(*args, **kwargs)

    return wrapped
