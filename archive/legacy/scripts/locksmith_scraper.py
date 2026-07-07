"""Texas locksmith B2B scraper — uses same engine as plumbing scraper."""
from pathlib import Path

import google_places_scraper as scraper

scraper.CATEGORY = "Locksmith"
scraper.TARGET_RECORDS = 10000
scraper.PLUMBING_KEYWORDS = [
    "locksmith",
    "locksmith service",
    "emergency locksmith",
    "car locksmith",
    "automotive locksmith",
    "commercial locksmith",
    "residential locksmith",
    "key cutting service",
    "lock repair service",
    "mobile locksmith",
]

base = Path(__file__).parent
output_dir = base / "texas_locksmith"
output_dir.mkdir(exist_ok=True)

scraper.PROGRESS_FILE = output_dir / "locksmith_progress.json"
scraper.OUTPUT_FILE = str(output_dir / "locksmith.csv")
scraper.CONTACT_OUTPUT_FILE = str(output_dir / "locksmith_contacts.csv")
scraper.PHONE_OUTPUT_FILE = str(output_dir / "locksmith_phones.txt")
scraper.EMAIL_OUTPUT_FILE = str(output_dir / "locksmith_emails.txt")

if __name__ == "__main__":
    scraper.main()
