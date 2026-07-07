"""Legacy CLI scraper — use the web app instead: start_scraper.bat"""

from pathlib import Path

from app.scraper_engine import ScraperEngine

# Backward-compatible defaults for Texas plumbing
TARGET_STATE = "Texas"
TARGET_RECORDS = 10000
CATEGORY = "Plumbing"
PLUMBING_KEYWORDS = [
    "plumber", "plumbing service", "plumbing company", "plumbing contractor",
    "emergency plumber", "commercial plumber", "drain cleaning service",
]


def log(message):
    print(message, flush=True)


def main():
    base = Path(__file__).parent
    export_dir = base / "data" / "exports" / "legacy_cli_plumbing"
    export_dir.mkdir(parents=True, exist_ok=True)

    engine = ScraperEngine(
        job_dir=export_dir,
        states=["Texas"],
        businesses=[{"name": CATEGORY, "keywords": PLUMBING_KEYWORDS}],
        target_records=TARGET_RECORDS,
        search_mode="cities",
        scrape_emails=False,
        headless=False,
        on_log=log,
    )
    result = engine.run()
    log(f"Done: {result}")


if __name__ == "__main__":
    main()
