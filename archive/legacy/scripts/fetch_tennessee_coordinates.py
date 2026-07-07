"""Run once to cache Tennessee city coordinates."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COORDS_CACHE_FILE = Path(__file__).parent / "tennessee_cities_coords.json"

TENNESSEE_CITIES = [
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
    "Mt Juliet", "White House", "Portsmouth", "Cleveland", "Lenoir City",
    "Alcoa", "Powell", "Hixson", "East Brainerd", "Red Oak",
]

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TennesseeTyreShopScraper/1.0"


def unique_cities():
    seen = set()
    cities = []
    for city in TENNESSEE_CITIES:
        key = city.lower()
        if key not in seen:
            seen.add(key)
            cities.append(city)
    return cities


def geocode_city(city):
    query = urllib.parse.urlencode({
        "city": city,
        "state": "Tennessee",
        "country": "USA",
        "format": "json",
        "limit": 1,
    })
    request = urllib.request.Request(
        f"{NOMINATIM_URL}?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if not data:
        return None

    return {
        "lat": float(data[0]["lat"]),
        "lng": float(data[0]["lon"]),
        "display_name": data[0].get("display_name", ""),
    }


def main():
    cached = {}
    if COORDS_CACHE_FILE.exists():
        cached = json.loads(COORDS_CACHE_FILE.read_text(encoding="utf-8"))

    cities = unique_cities()
    missing = [city for city in cities if city not in cached]

    print(f"Cities total: {len(cities)}")
    print(f"Already cached: {len(cached)}")
    print(f"To geocode: {len(missing)}")

    for index, city in enumerate(missing, start=1):
        print(f"[{index}/{len(missing)}] Geocoding {city}...")
        try:
            result = geocode_city(city)
            if result:
                cached[city] = result
                print(f"  -> {result['lat']}, {result['lng']}")
            else:
                print("  -> not found")
        except Exception as exc:
            print(f"  -> error: {exc}")

        COORDS_CACHE_FILE.write_text(
            json.dumps(cached, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        time.sleep(1.2)

    print(f"\nSaved {len(cached)} cities to {COORDS_CACHE_FILE}")


if __name__ == "__main__":
    main()
