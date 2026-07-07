"""Ensure Python packages and Playwright Chrome are installed."""

import subprocess
import sys
from pathlib import Path

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


def ensure_playwright_chrome() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            browser.close()
        print("[setup] Playwright Chrome is ready")
        return True
    except Exception:
        return _run(
            [sys.executable, "-m", "playwright", "install", "chrome"],
            "Installing Playwright Chrome browser",
        )


def ensure_all() -> bool:
    ok = ensure_pip_packages()
    ok = ensure_playwright_chrome() and ok
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if ensure_all() else 1)
