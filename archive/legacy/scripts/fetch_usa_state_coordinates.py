"""Run once to cache US state center coordinates."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COORDS_CACHE_FILE = Path(__file__).parent / "usa_states_coords.json"

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

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "USARetailShopScraper/1.0"


def geocode_state(state):
    query = urllib.parse.urlencode({
        "state": state,
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

    missing = [state for state in US_STATES if state not in cached]
    print(f"States total: {len(US_STATES)}")
    print(f"Already cached: {len(cached)}")
    print(f"To geocode: {len(missing)}")

    for index, state in enumerate(missing, start=1):
        print(f"[{index}/{len(missing)}] Geocoding {state}...")
        try:
            result = geocode_state(state)
            if result:
                cached[state] = result
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

    print(f"\nSaved {len(cached)} states to {COORDS_CACHE_FILE}")


if __name__ == "__main__":
    main()
