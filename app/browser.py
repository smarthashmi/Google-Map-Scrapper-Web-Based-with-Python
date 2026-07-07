"""Playwright browser launcher — Chrome on Windows, bundled Chromium on Linux."""

import sys


def launch_chromium(playwright, *, headless: bool = True):
    if sys.platform == "win32":
        try:
            return playwright.chromium.launch(headless=headless, channel="chrome")
        except Exception:
            pass
    return playwright.chromium.launch(headless=headless)
