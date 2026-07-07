"""Ensure Python packages and Playwright browser are installed."""

import subprocess
import sys
from pathlib import Path

from app.browser import launch_chromium

BASE_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS = BASE_DIR / "requirements.txt"


def _run(cmd: list[str], label: str) -> bool:
    print(f"[setup] {label}...")
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[setup] Failed: {label} (exit {exc.returncode})")
        return False


def ensure_pip_packages() -> bool:
    if not REQUIREMENTS.exists():
        return True
    return _run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)],
        "Installing Python packages",
    )


def ensure_playwright_browser() -> bool:
    browser_name = "chrome" if sys.platform == "win32" else "chromium"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = launch_chromium(playwright, headless=True)
            browser.close()
        print(f"[setup] Playwright {browser_name} is ready")
        return True
    except Exception:
        return _run(
            [sys.executable, "-m", "playwright", "install", browser_name],
            f"Installing Playwright {browser_name} browser",
        )


def ensure_all() -> bool:
    ok = ensure_pip_packages()
    ok = ensure_playwright_browser() and ok
    if sys.platform != "win32":
        _run(
            [sys.executable, "-m", "playwright", "install-deps", "chromium"],
            "Installing Playwright system dependencies",
        )
    return ok


if __name__ == "__main__":
    sys.exit(0 if ensure_all() else 1)
