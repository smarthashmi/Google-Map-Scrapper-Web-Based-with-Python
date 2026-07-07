"""USA retail shop scraper — all 50 states."""
import json
from pathlib import Path

import google_places_scraper as scraper

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]

RETAIL_KEYWORDS = [
    "retail shop",
    "retail store",
    "clothing store",
    "general store",
    "convenience store",
]

base = Path(__file__).parent
output_dir = base / "usa_retail"
output_dir.mkdir(exist_ok=True)

scraper.TARGET_STATE = "USA"
scraper.CATEGORY = "Retail Shop"
scraper.TARGET_RECORDS = 10000
scraper.TEXAS_CITIES = US_STATES
scraper.LARGE_CITIES = {
    "California", "Texas", "Florida", "New York", "Pennsylvania",
    "Illinois", "Ohio", "Georgia", "North Carolina", "Michigan",
}
scraper.MEDIUM_CITIES = {
    "Virginia", "Washington", "Arizona", "Massachusetts", "Tennessee",
    "Indiana", "Missouri", "Maryland", "Wisconsin", "Colorado",
    "Minnesota", "South Carolina", "Alabama", "Louisiana", "Kentucky",
    "Oregon", "Oklahoma", "Connecticut", "Utah", "Iowa", "Nevada",
    "Arkansas", "Mississippi", "Kansas", "New Mexico", "Nebraska",
}
scraper.PLUMBING_KEYWORDS = RETAIL_KEYWORDS

scraper.COORDS_CACHE_FILE = base / "usa_states_coords.json"
scraper.PROGRESS_FILE = output_dir / "retail_progress.json"
scraper.OUTPUT_FILE = str(output_dir / "retail_shops.csv")
scraper.CONTACT_OUTPUT_FILE = str(output_dir / "retail_shops_contacts.csv")
scraper.PHONE_OUTPUT_FILE = str(output_dir / "retail_shops_phones.txt")
scraper.EMAIL_OUTPUT_FILE = str(output_dir / "retail_shops_emails.txt")


def build_retail_searches(coords):
    searches = []
    for state in US_STATES:
        center = coords[state]
        offsets = scraper.grid_offsets_for_city(state)

        for dlat, dlng in offsets:
            search_lat = round(center["lat"] + dlat, 6)
            search_lng = round(center["lng"] + dlng, 6)

            for keyword in RETAIL_KEYWORDS:
                query = f"{keyword} in {state}, USA"
                searches.append({
                    "state": state,
                    "city": state,
                    "keyword": query,
                    "search_lat": search_lat,
                    "search_lng": search_lng,
                    "query_label": f"{query} @{search_lat},{search_lng}",
                })

    return searches


def migrate_old_retail_data():
    old_file = base / "usa_retail_shops_all_states.csv"
    new_file = Path(scraper.OUTPUT_FILE)

    if not old_file.exists() or new_file.exists():
        return

    import pandas as pd

    def clean(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        return str(value).strip()

    old_df = pd.read_csv(old_file)
    records = []
    for row in old_df.to_dict("records"):
        state = clean(row.get("State", ""))
        query = clean(row.get("Search Query", "")) or f"retail shop in {state}, USA"
        address = clean(row.get("Address", ""))
        records.append({
            "State": state,
            "City": state,
            "Category": "Retail Shop",
            "Search Keyword": query,
            "Search Latitude": "",
            "Search Longitude": "",
            "Business Name": clean(row.get("Business Name", "")),
            "Address": address,
            "Zip Code": scraper.parse_zip_code(address),
            "Phone": clean(row.get("Phone", "")),
            "Email": "",
            "Website": clean(row.get("Website", "")),
            "Rating": clean(row.get("Rating", "")),
            "Reviews": clean(row.get("Reviews", "")),
            "Business Hours": "",
            "Business Status": "",
            "Google Categories": "",
            "Place URL": clean(row.get("Place URL", "")),
        })

    new_df = pd.DataFrame(records)
    for col in scraper.CSV_COLUMNS:
        if col not in new_df.columns:
            new_df[col] = ""
    new_df = new_df[scraper.CSV_COLUMNS]
    new_df.to_csv(new_file, index=False, encoding="utf-8-sig")
    print(f"Migrated {len(new_df)} records to {new_file}")


def seed_progress_from_existing():
    import pandas as pd

    output_file = Path(scraper.OUTPUT_FILE)
    if not output_file.exists():
        return

    coords = json.loads(scraper.COORDS_CACHE_FILE.read_text(encoding="utf-8"))
    df = pd.read_csv(output_file)
    if df.empty:
        return

    completed = scraper.load_completed_searches()
    for state in df["State"].dropna().unique():
        if state not in coords:
            continue
        center = coords[state]
        key = scraper.search_key(
            state,
            f"retail shop in {state}, USA",
            center["lat"],
            center["lng"],
        )
        completed.add(key)

    scraper.save_completed_searches(completed)
    print(f"Seeded {len(completed)} completed searches from existing data")


scraper.build_searches = build_retail_searches
scraper.unique_cities = lambda: US_STATES

if __name__ == "__main__":
    migrate_old_retail_data()
    if scraper.COORDS_CACHE_FILE.exists() and not scraper.PROGRESS_FILE.exists():
        seed_progress_from_existing()
    scraper.main()
