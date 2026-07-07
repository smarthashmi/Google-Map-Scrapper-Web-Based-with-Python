from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
COORDS_DIR = DATA_DIR / "coords"
JOBS_DIR = DATA_DIR / "jobs"
EXPORTS_DIR = DATA_DIR / "exports"
ARCHIVE_DIR = BASE_DIR / "archive" / "legacy"
AUTH_FILE = DATA_DIR / "auth.json"
CRM_DIR = DATA_DIR / "crm"

for directory in (COORDS_DIR, JOBS_DIR, EXPORTS_DIR, ARCHIVE_DIR, CRM_DIR):
    directory.mkdir(parents=True, exist_ok=True)

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

LARGE_STATES = {
    "California", "Texas", "Florida", "New York", "Pennsylvania",
    "Illinois", "Ohio", "Georgia", "North Carolina", "Michigan",
}

MEDIUM_STATES = {
    "Virginia", "Washington", "Arizona", "Massachusetts", "Tennessee",
    "Indiana", "Missouri", "Maryland", "Wisconsin", "Colorado",
    "Minnesota", "South Carolina", "Alabama", "Louisiana", "Kentucky",
    "Oregon", "Oklahoma", "Connecticut", "Utah", "Iowa", "Nevada",
    "Arkansas", "Mississippi", "Kansas", "New Mexico", "Nebraska",
}

LARGE_GRID_OFFSETS = [
    (0, 0), (0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05),
    (0.035, 0.035), (-0.035, 0.035), (0.035, -0.035), (-0.035, -0.035),
]

MEDIUM_GRID_OFFSETS = [
    (0, 0), (0.04, 0), (-0.04, 0), (0, 0.04), (0, -0.04),
]

# Lat/lng grid density — each location is searched from multiple coordinate points
GRID_DENSITY = {
    "light": {"rings": 1, "step": 0.06, "label": "Light — 9 points per area (~6 km spacing)"},
    "standard": {"rings": 2, "step": 0.04, "label": "Standard — 25 points per area (~4 km spacing)"},
    "deep": {"rings": 3, "step": 0.03, "label": "Deep — 49 points per area (~3 km spacing)"},
    "ultra": {"rings": 4, "step": 0.022, "label": "Ultra — 81 points per area (~2.4 km spacing)"},
}

STATE_CAPITALS = {
    "Alabama": "Montgomery", "Alaska": "Juneau", "Arizona": "Phoenix", "Arkansas": "Little Rock",
    "California": "Sacramento", "Colorado": "Denver", "Connecticut": "Hartford", "Delaware": "Dover",
    "Florida": "Tallahassee", "Georgia": "Atlanta", "Hawaii": "Honolulu", "Idaho": "Boise",
    "Illinois": "Springfield", "Indiana": "Indianapolis", "Iowa": "Des Moines", "Kansas": "Topeka",
    "Kentucky": "Frankfort", "Louisiana": "Baton Rouge", "Maine": "Augusta", "Maryland": "Annapolis",
    "Massachusetts": "Boston", "Michigan": "Lansing", "Minnesota": "Saint Paul", "Mississippi": "Jackson",
    "Missouri": "Jefferson City", "Montana": "Helena", "Nebraska": "Lincoln", "Nevada": "Carson City",
    "New Hampshire": "Concord", "New Jersey": "Trenton", "New Mexico": "Santa Fe", "New York": "Albany",
    "North Carolina": "Raleigh", "North Dakota": "Bismarck", "Ohio": "Columbus", "Oklahoma": "Oklahoma City",
    "Oregon": "Salem", "Pennsylvania": "Harrisburg", "Rhode Island": "Providence",
    "South Carolina": "Columbia", "South Dakota": "Pierre", "Tennessee": "Nashville", "Texas": "Austin",
    "Utah": "Salt Lake City", "Vermont": "Montgomery", "Virginia": "Richmond", "Washington": "Olympia",
    "West Virginia": "Charleston", "Wisconsin": "Madison", "Wyoming": "Cheyenne",
}

# Fix Vermont capital typo
STATE_CAPITALS["Vermont"] = "Montpelier"

BUSINESS_PRESETS = {
    "Plumbing": [
        "plumber", "plumbing service", "plumbing company", "plumbing contractor",
        "emergency plumber", "commercial plumber", "drain cleaning service",
        "septic service", "water heater repair", "pipe repair service",
    ],
    "Locksmith": [
        "locksmith", "locksmith service", "emergency locksmith", "car locksmith",
        "automotive locksmith", "commercial locksmith", "residential locksmith",
        "key cutting service", "lock repair service", "mobile locksmith",
    ],
    "Retail Shop": [
        "retail shop", "retail store", "clothing store", "general store",
        "convenience store",
    ],
    "Tyre Shop": [
        "tire shop", "tyre shop", "tire store", "auto tire shop",
        "tire service", "tire repair shop", "wheel and tire shop",
    ],
    "Auto Repair": [
        "auto repair shop", "car repair", "automotive repair", "mechanic shop",
        "oil change service", "brake repair", "transmission repair",
    ],
    "Restaurant": [
        "restaurant", "family restaurant", "fast food restaurant",
        "pizza restaurant", "mexican restaurant", "chinese restaurant",
    ],
}

CSV_COLUMNS = [
    "State", "City", "County", "Category", "Business Name", "Phone", "Email",
    "Address", "Zip Code", "Website", "Rating", "Reviews",
    "Business Hours", "Business Status", "Google Categories",
    "Search Keyword", "Search Latitude", "Search Longitude", "Place URL",
]

STATE_COORDS_FILE = COORDS_DIR / "usa_states_coords.json"
TEXAS_CITIES_COORDS_FILE = COORDS_DIR / "texas_cities_coords.json"
TENNESSEE_CITIES_COORDS_FILE = COORDS_DIR / "tennessee_cities_coords.json"

FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5050

SPEED_PRESETS = {
    "safe": {
        "label": "Safe — lowest block risk",
        "runners": 1,
        "delay_between_leads": 2.5,
        "delay_between_searches": 5.0,
        "delay_between_scrolls": 1.8,
    },
    "balanced": {
        "label": "Balanced — recommended",
        "runners": 2,
        "delay_between_leads": 1.5,
        "delay_between_searches": 3.0,
        "delay_between_scrolls": 1.5,
    },
    "fast": {
        "label": "Fast — higher block risk",
        "runners": 3,
        "delay_between_leads": 0.8,
        "delay_between_searches": 2.0,
        "delay_between_scrolls": 1.0,
    },
}
