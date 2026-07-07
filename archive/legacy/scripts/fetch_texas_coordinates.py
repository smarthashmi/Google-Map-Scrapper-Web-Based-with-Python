"""Run once to cache Texas city coordinates. Re-run only to add new cities."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COORDS_CACHE_FILE = Path(__file__).parent / "texas_cities_coords.json"

TEXAS_CITIES = [
    "Houston", "Dallas", "San Antonio", "Austin", "Fort Worth", "El Paso",
    "Arlington", "Corpus Christi", "Plano", "Laredo", "Lubbock", "Garland",
    "Irving", "Amarillo", "Grand Prairie", "Brownsville", "Pasadena",
    "McKinney", "Mesquite", "McAllen", "Killeen", "Frisco", "Waco",
    "Carrollton", "Denton", "Midland", "Abilene", "Beaumont", "Round Rock",
    "Odessa", "Richardson", "League City", "Sugar Land", "Tyler", "Allen",
    "Lewisville", "San Angelo", "Edinburg", "College Station", "Pearland",
    "Wichita Falls", "Bryan", "Mission", "Longview", "Baytown", "Pharr",
    "Temple", "Missouri City", "Flower Mound", "New Braunfels",
    "North Richland Hills", "Cedar Park", "Conroe", "Georgetown",
    "Pflugerville", "Port Arthur", "Euless", "DeSoto", "Grapevine",
    "Galveston", "Katy", "The Woodlands", "Cypress", "Spring", "Humble",
    "Tomball", "Kingwood", "Stafford", "Richmond", "Rosenberg",
    "Victoria", "Harlingen", "Sherman", "Texarkana", "Keller", "Rockwall",
    "Burleson", "Mansfield", "Rowlett", "Leander", "Lake Jackson", "Texas City",
    "Del Rio", "Lufkin", "Nacogdoches", "Eagle Pass", "Weslaco",
    "Coppell", "Bedford", "Hurst", "Colleyville", "Southlake", "Duncanville",
    "Farmers Branch", "Addison", "Balch Springs", "Cedar Hill", "Lancaster",
    "Greenville", "Paris", "Ennis", "Cleburne", "Weatherford",
    "Stephenville", "Mineral Wells", "Big Spring", "Snyder", "Plainview",
    "Hereford", "Canyon", "Pampa", "Borger", "Dumas", "Uvalde", "Kerrville",
    "Fredericksburg", "Seguin", "San Marcos", "Kyle", "Buda", "Lockhart",
    "Bastrop", "Huntsville", "Marshall", "Palestine", "Corsicana", "Athens",
    "Jacksonville", "Kilgore", "Mount Pleasant", "Sulphur Springs",
]

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "TexasPlumbingB2BScraper/1.0"


def unique_cities():
    seen = set()
    cities = []
    for city in TEXAS_CITIES:
        key = city.lower()
        if key not in seen:
            seen.add(key)
            cities.append(city)
    return cities


def geocode_city(city):
    query = urllib.parse.urlencode({
        "city": city,
        "state": "Texas",
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
                print(f"  -> not found")
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
