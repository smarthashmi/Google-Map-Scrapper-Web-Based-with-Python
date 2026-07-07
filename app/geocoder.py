"""Geocoding with county, city, latitude & longitude grid coverage."""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from app.config import (
    COORDS_DIR,
    GRID_DENSITY,
    LARGE_GRID_OFFSETS,
    LARGE_STATES,
    MEDIUM_GRID_OFFSETS,
    MEDIUM_STATES,
    STATE_CAPITALS,
    STATE_COORDS_FILE,
    TENNESSEE_CITIES_COORDS_FILE,
    TEXAS_CITIES_COORDS_FILE,
    US_STATES,
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "BusinessScraperWeb/2.0"

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
    "Mt Juliet", "White House", "Hixson", "Alcoa", "Powell", "Lenoir City",
]

STATE_CITY_LISTS = {"Texas": TEXAS_CITIES, "Tennessee": TENNESSEE_CITIES}

STATE_CITY_COORD_FILES = {
    "Texas": TEXAS_CITIES_COORDS_FILE,
    "Tennessee": TENNESSEE_CITIES_COORDS_FILE,
}

LARGE_CITY_NAMES = {
    "Houston", "Dallas", "San Antonio", "Austin", "Fort Worth", "El Paso",
    "Nashville", "Memphis", "Knoxville", "Chattanooga", "Phoenix", "Los Angeles",
    "Chicago", "New York", "Philadelphia", "Atlanta", "Miami", "Seattle",
}

MEDIUM_CITY_NAMES = {
    "Arlington", "Corpus Christi", "Plano", "McKinney", "Frisco",
    "Murfreesboro", "Franklin", "Jackson", "Johnson City", "Montgomery",
    "Birmingham", "Tampa", "Orlando", "Denver", "Portland",
}


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _normalize_county(raw: str) -> str:
    if not raw:
        return ""
    county = raw.strip()
    county = re.sub(r"\s+County$", "", county, flags=re.IGNORECASE)
    return county.strip()


def _parse_nominatim_item(item: dict) -> dict:
    addr = item.get("address") or {}
    county = (
        addr.get("county")
        or addr.get("city_district")
        or addr.get("state_district")
        or ""
    )
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("hamlet")
        or addr.get("municipality")
        or ""
    )
    return {
        "lat": float(item["lat"]),
        "lng": float(item["lon"]),
        "display_name": item.get("display_name", ""),
        "county": _normalize_county(county),
        "city": city,
    }


def _nominatim_search(params: dict) -> dict | None:
    params = {**params, "format": "json", "limit": 1, "addressdetails": 1}
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{NOMINATIM_URL}?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not data:
        return None
    return _parse_nominatim_item(data[0])


def generate_lat_lng_grid(density: str = "standard") -> list[tuple[float, float]]:
    """Build coordinate offsets around a center point for deep area coverage."""
    cfg = GRID_DENSITY.get(density, GRID_DENSITY["standard"])
    rings, step = cfg["rings"], cfg["step"]
    offsets = []
    for ring_lat in range(-rings, rings + 1):
        for ring_lng in range(-rings, rings + 1):
            offsets.append((round(ring_lat * step, 6), round(ring_lng * step, 6)))
    return offsets


def grid_offsets_for_location(
    state: str,
    location_name: str,
    search_mode: str,
    grid_density: str = "standard",
) -> list[tuple[float, float]]:
    """Return lat/lng offset grid for a location. Always uses coordinate grid for depth."""
    if grid_density in GRID_DENSITY:
        base = generate_lat_lng_grid(grid_density)
    else:
        base = generate_lat_lng_grid("standard")

    if search_mode == "cities":
        if location_name in LARGE_CITY_NAMES:
            extra = generate_lat_lng_grid("deep") if grid_density != "ultra" else base
            return _merge_offsets(base, extra)
        if location_name in MEDIUM_CITY_NAMES:
            return base
        if grid_density in ("light",):
            return generate_lat_lng_grid("light")
        return base

    if state in LARGE_STATES and grid_density in ("standard", "deep", "ultra"):
        wide = generate_lat_lng_grid("deep" if grid_density == "ultra" else grid_density)
        return _merge_offsets(base, wide)
    if state in MEDIUM_STATES:
        return base
    return generate_lat_lng_grid("light") if grid_density == "light" else base


def _merge_offsets(primary: list, secondary: list) -> list:
    seen = set()
    merged = []
    for dlat, dlng in primary + secondary:
        key = (round(dlat, 5), round(dlng, 5))
        if key not in seen:
            seen.add(key)
            merged.append((dlat, dlng))
    return merged


def parse_county_from_address(address: str) -> str:
    if not address:
        return ""
    match = re.search(r"([^,]+)\s+County", address, re.IGNORECASE)
    if match:
        return _normalize_county(match.group(1))
    return ""


def ensure_state_coordinates(on_progress=None) -> dict:
    cached = _load_json(STATE_COORDS_FILE)
    missing = [state for state in US_STATES if state not in cached]

    for index, state in enumerate(missing, start=1):
        if on_progress:
            on_progress(f"Geocoding state {state} ({index}/{len(missing)})")
        try:
            result = _nominatim_search({"state": state, "country": "USA"})
            if result:
                result["name"] = state
                cached[state] = result
        except Exception:
            pass
        _save_json(STATE_COORDS_FILE, cached)
        time.sleep(1.2)

    return cached


def _coord_file_for_state(state: str) -> Path:
    return STATE_CITY_COORD_FILES.get(
        state, COORDS_DIR / f"{state.lower().replace(' ', '_')}_cities_coords.json"
    )


def ensure_city_coordinates(state: str, cities: list[str], on_progress=None) -> dict:
    if not cities:
        return {}

    coord_file = _coord_file_for_state(state)
    cached = _load_json(coord_file)
    missing = []
    seen = set()
    updated = False
    for city in cities:
        key = city.lower()
        if key not in seen:
            seen.add(key)
            if city in cached:
                entry = cached[city]
                if not entry.get("county"):
                    county = parse_county_from_address(entry.get("display_name", ""))
                    if county:
                        entry["county"] = county
                        cached[city] = entry
                        updated = True
            else:
                missing.append(city)

    if updated:
        _save_json(coord_file, cached)

    for index, city in enumerate(missing, start=1):
        if on_progress:
            on_progress(f"Geocoding {city}, {state} ({index}/{len(missing)})")
        try:
            result = _nominatim_search({
                "city": city, "state": state, "country": "USA",
            })
            if result:
                result["name"] = city
                if not result.get("county"):
                    result["county"] = parse_county_from_address(result.get("display_name", ""))
                cached[city] = result
        except Exception:
            pass
        _save_json(coord_file, cached)
        time.sleep(1.2)

    return cached


def _cities_for_state(state: str, search_mode: str) -> list[str]:
    if search_mode == "cities":
        if state in STATE_CITY_LISTS:
            return STATE_CITY_LISTS[state]
        capital = STATE_CAPITALS.get(state)
        return [capital] if capital else [state]
    return []


def get_locations_for_state(state: str, search_mode: str) -> list[dict]:
    """Return locations with city, county, latitude, longitude."""
    state_coords = _load_json(STATE_COORDS_FILE)
    if state not in state_coords:
        state_coords = ensure_state_coordinates()
    if state not in state_coords:
        return []

    cities = _cities_for_state(state, search_mode)
    if cities:
        city_coords = ensure_city_coordinates(state, cities)
        locations = []
        for city in cities:
            if city not in city_coords:
                continue
            entry = city_coords[city]
            locations.append({
                "name": city,
                "state": state,
                "county": entry.get("county", ""),
                "lat": entry["lat"],
                "lng": entry["lng"],
            })
        if locations:
            return locations

    center = state_coords[state]
    county = center.get("county", "") or parse_county_from_address(center.get("display_name", ""))
    return [{
        "name": STATE_CAPITALS.get(state, state),
        "state": state,
        "county": county,
        "lat": center["lat"],
        "lng": center["lng"],
    }]
