"""Tennessee tyre/tire shop B2B scraper."""
from pathlib import Path

import google_places_scraper as scraper

scraper.TARGET_STATE = "Tennessee"
scraper.CATEGORY = "Tyre Shop"
scraper.TARGET_RECORDS = 10000
scraper.PLUMBING_KEYWORDS = [
    "tire shop",
    "tyre shop",
    "tire store",
    "auto tire shop",
    "tire service",
    "tire repair shop",
    "wheel and tire shop",
    "commercial tire shop",
    "tire dealer",
    "used tire shop",
]

scraper.TEXAS_CITIES = [
    "Nashville", "Memphis", "Knoxville", "Chattanooga", "Clarksville",
    "Murfreesboro", "Franklin", "Jackson", "Johnson City", "Bartlett",
    "Hendersonville", "Kingsport", "Collierville", "Cleveland", "Smyrna",
    "Germantown", "Brentwood", "Columbia", "La Vergne", "Gallatin",
    "Cookeville", "Mount Juliet", "Lebanon", "Morristown", "Oak Ridge",
    "Maryville", "Bristol", "Farragut", "Shelbyville", "Tullahoma",
    "Spring Hill", "Goodlettsville", "Dyersburg", "Sevierville", "Dickson",
    "Greeneville", "Elizabethton", "Athens", "McMinnville", "Crossville",
    "Portland", "Soddy-Daisy", "Red Bank", "East Ridge", "Middle Valley",
    "Manchester", "Union City", "Martin", "Paris", "Lexington",
    "Lawrenceburg", "Pulaski", "Winchester", "Millington", "Arlington",
    "Lakeland", "Cordova", "Antioch", "Hermitage", "Madison",
    "Mt Juliet", "White House", "Hixson", "Alcoa", "Powell",
    "Lenoir City", "Dyersburg", "Sevierville",
]

scraper.LARGE_CITIES = {
    "Nashville", "Memphis", "Knoxville", "Chattanooga", "Clarksville",
    "Murfreesboro", "Franklin", "Jackson", "Johnson City", "Bartlett",
    "Hendersonville", "Kingsport", "Collierville", "Smyrna", "Germantown",
}

scraper.MEDIUM_CITIES = {
    "Brentwood", "Columbia", "La Vergne", "Gallatin", "Cookeville",
    "Mount Juliet", "Lebanon", "Morristown", "Oak Ridge", "Maryville",
    "Bristol", "Farragut", "Shelbyville", "Spring Hill", "Goodlettsville",
    "Antioch", "Cordova", "Madison", "Hermitage",
}

base = Path(__file__).parent
output_dir = base / "tennessee_tyre"
output_dir.mkdir(exist_ok=True)

scraper.COORDS_CACHE_FILE = base / "tennessee_cities_coords.json"
scraper.PROGRESS_FILE = output_dir / "tyre_shops_progress.json"
scraper.OUTPUT_FILE = str(output_dir / "tyre_shops.csv")
scraper.CONTACT_OUTPUT_FILE = str(output_dir / "tyre_shops_contacts.csv")
scraper.PHONE_OUTPUT_FILE = str(output_dir / "tyre_shops_phones.txt")
scraper.EMAIL_OUTPUT_FILE = str(output_dir / "tyre_shops_emails.txt")

if __name__ == "__main__":
    scraper.main()
