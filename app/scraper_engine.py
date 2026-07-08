"""Google Maps Places scraper engine with resume support."""

import json
import re
import threading
import time
import urllib.parse
from pathlib import Path
from queue import Queue
from typing import Callable

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.browser import launch_chromium
from app.config import CSV_COLUMNS
from app.geocoder import (
    get_locations_for_state,
    grid_offsets_for_location,
    parse_county_from_address,
)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(
    r"(?:\+1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}"
)
ZIP_PATTERN = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
JUNK_EMAIL_DOMAINS = (
    "example.com", "sentry.io", "domain.com", "email.com",
    "yourdomain.com", "test.com",
)

MAX_SCROLLS = 35
MAP_ZOOM = 13
DELAY_BETWEEN_PLACES = 1.0
WEBSITE_EMAIL_TIMEOUT = 8000


def is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    email = email.lower().strip()
    if any(email.endswith(f"@{domain}") for domain in JUNK_EMAIL_DOMAINS):
        return False
    if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return False
    return bool(EMAIL_PATTERN.fullmatch(email))


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    compact = re.sub(r"[\s().-]", "", phone)
    digits = re.sub(r"\D", "", phone)
    # Exclude Pakistan numbers from all outputs.
    if compact.startswith("+92") or digits.startswith("0092") or (
        digits.startswith("92") and len(digits) > 10
    ):
        return ""
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1{digits}"
    if phone.startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    return phone


def clean_contact_field(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def parse_zip_code(address: str) -> str:
    match = ZIP_PATTERN.search(address or "")
    return match.group(1) if match else ""


def search_key(state: str, city: str, category: str, keyword: str, lat: float, lng: float) -> tuple:
    return (state, city, category, keyword, round(float(lat), 6), round(float(lng), 6))


def build_searches(
    states: list,
    businesses: list,
    search_mode: str,
    grid_density: str = "standard",
) -> list:
    searches = []
    for state in states:
        locations = get_locations_for_state(state, search_mode)
        for location in locations:
            offsets = grid_offsets_for_location(
                state, location["name"], search_mode, grid_density
            )
            for business in businesses:
                category = business["name"]
                for keyword in business["keywords"]:
                    display_keyword = keyword
                    if search_mode == "state":
                        display_keyword = f"{keyword} in {state}, USA"
                    for dlat, dlng in offsets:
                        search_lat = round(location["lat"] + dlat, 6)
                        search_lng = round(location["lng"] + dlng, 6)
                        searches.append({
                            "state": state,
                            "city": location["name"],
                            "county": location.get("county", ""),
                            "category": category,
                            "keyword": display_keyword,
                            "raw_keyword": keyword,
                            "search_lat": search_lat,
                            "search_lng": search_lng,
                            "center_lat": location["lat"],
                            "center_lng": location["lng"],
                            "query_label": (
                                f"{display_keyword} @ {search_lat},{search_lng} "
                                f"({location['name']}, {location.get('county', '') or state})"
                            ),
                        })
    return searches


def build_maps_search_url(keyword: str, lat: float, lng: float, zoom: int = MAP_ZOOM) -> str:
    encoded = urllib.parse.quote(keyword)
    return f"https://www.google.com/maps/search/{encoded}/@{lat},{lng},{zoom}z"


class ScraperEngine:
    def __init__(
        self,
        job_dir: Path,
        states: list,
        businesses: list,
        target_records: int = 10000,
        search_mode: str = "state",
        grid_density: str = "standard",
        scrape_website_emails: bool = False,
        headless: bool = True,
        min_rating: float = 0,
        min_reviews: int = 0,
        runners: int = 1,
        delay_between_leads: float = 1.5,
        delay_between_searches: float = 3.0,
        delay_between_scrolls: float = 1.5,
        on_log: Callable = None,
        on_error: Callable = None,
        on_record: Callable = None,
        on_progress: Callable = None,
        should_stop: Callable = None,
    ):
        self.job_dir = Path(job_dir)
        self.states = states
        self.businesses = businesses
        self.target_records = target_records
        self.search_mode = search_mode
        self.grid_density = grid_density
        self.scrape_website_emails = scrape_website_emails
        self.headless = headless
        self.min_rating = float(min_rating or 0)
        self.min_reviews = int(min_reviews or 0)
        self.runners = max(1, min(6, int(runners or 1)))
        self.delay_between_leads = float(delay_between_leads)
        self.delay_between_searches = float(delay_between_searches)
        self.delay_between_scrolls = float(delay_between_scrolls)
        self.on_log = on_log or (lambda msg: None)
        self.on_error = on_error or (lambda msg: None)
        self.on_record = on_record or (lambda record: None)
        self.on_progress = on_progress or (lambda data: None)
        self.should_stop = should_stop or (lambda: False)
        self._data_lock = threading.Lock()
        self._browser_lock = threading.Lock()
        self._active_browsers: list = []
        self._final_data_cache: list = []

        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.by_state_dir = self.job_dir / "by_state"
        self.by_city_dir = self.job_dir / "by_city"
        self.by_county_dir = self.job_dir / "by_county"
        self.by_state_dir.mkdir(exist_ok=True)
        self.by_city_dir.mkdir(exist_ok=True)
        self.by_county_dir.mkdir(exist_ok=True)

        self.progress_file = self.job_dir / "progress.json"
        self.history_file = self.job_dir / "history.json"
        self.output_file = self.job_dir / "businesses.csv"
        self.contacts_file = self.job_dir / "contacts.csv"
        self.phones_file = self.job_dir / "phones.txt"
        self.emails_file = self.job_dir / "emails.txt"

    def log(self, message: str) -> None:
        self.on_log(message)

    def error(self, message: str) -> None:
        self.on_error(message)
        self.on_log(f"ERROR: {message}")

    def register_browser(self, browser) -> None:
        with self._browser_lock:
            self._active_browsers.append(browser)

    def force_stop(self) -> None:
        with self._browser_lock:
            for browser in self._active_browsers:
                try:
                    browser.close()
                except Exception:
                    pass
            self._active_browsers.clear()
        if self._final_data_cache:
            self.save_all_data(self._final_data_cache)

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep in small chunks. Returns True if stop was requested."""
        remaining = max(0.0, float(seconds))
        if remaining == 0:
            return self.should_stop()
        while remaining > 0:
            if self.should_stop():
                return True
            chunk = min(0.25, remaining)
            time.sleep(chunk)
            remaining -= chunk
        return self.should_stop()

    def _load_completed(self) -> set:
        if self.progress_file.exists():
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            return {tuple(item) for item in data.get("completed", [])}
        return set()

    def _save_completed(self, completed: set) -> None:
        payload = {"completed": [list(item) for item in sorted(completed)], "count": len(completed)}
        self.progress_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_history(self) -> list:
        if self.history_file.exists():
            return json.loads(self.history_file.read_text(encoding="utf-8"))
        return []

    def _append_history(self, entry: dict) -> None:
        history = self._load_history()
        history.append(entry)
        self.history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_records(self):
        completed = self._load_completed()
        if not self.output_file.exists():
            return [], set(), completed
        df = pd.read_csv(self.output_file)
        if df.empty:
            return [], set(), completed
        records = df.to_dict("records")
        seen_urls = set(df["Place URL"].dropna().astype(str))
        return records, seen_urls, completed

    def _filter_pending(self, searches: list, completed: set):
        start_index = 0
        for index, search_meta in enumerate(searches):
            key = search_key(
                search_meta["state"], search_meta["city"], search_meta["category"],
                search_meta["keyword"], search_meta["search_lat"], search_meta["search_lng"],
            )
            if key in completed:
                start_index = index + 1
        pending = []
        for search_meta in searches[start_index:]:
            key = search_key(
                search_meta["state"], search_meta["city"], search_meta["category"],
                search_meta["keyword"], search_meta["search_lat"], search_meta["search_lng"],
            )
            if key not in completed:
                pending.append(search_meta)
        return pending, start_index

    def _accept_cookies(self, page) -> None:
        for label in ("Accept all", "Reject all", "I agree"):
            button = page.get_by_role("button", name=label)
            if button.count() > 0:
                try:
                    button.first.click(timeout=3000)
                    if self._interruptible_sleep(1):
                        return
                except PlaywrightTimeout:
                    pass

    def _scroll_results_feed(self, page) -> None:
        feed = page.locator('div[role="feed"]')
        if feed.count() == 0:
            return
        last_count = 0
        stale_rounds = 0
        for _ in range(MAX_SCROLLS):
            if self.should_stop():
                break
            if page.locator("text=You've reached the end of the list").count() > 0:
                break
            feed.first.evaluate("el => el.scrollTop = el.scrollHeight")
            if self._interruptible_sleep(self.delay_between_scrolls):
                break
            current_count = page.locator('a[href*="/maps/place/"]').count()
            if current_count == last_count:
                stale_rounds += 1
                if stale_rounds >= 3:
                    break
            else:
                stale_rounds = 0
                last_count = current_count

    def _collect_place_links(self, page) -> list:
        links = page.locator('a[href*="/maps/place/"]')
        seen = set()
        place_urls = []
        for i in range(links.count()):
            href = links.nth(i).get_attribute("href")
            if not href or "/maps/place/" not in href:
                continue
            clean_url = href.split("?")[0]
            if clean_url in seen:
                continue
            seen.add(clean_url)
            place_urls.append(clean_url)
        return place_urls

    def _extract_phone(self, page) -> str:
        candidates = []
        phone_buttons = page.locator('button[data-item-id^="phone:"]')
        for i in range(phone_buttons.count()):
            item_id = phone_buttons.nth(i).get_attribute("data-item-id") or ""
            if "tel:" in item_id:
                candidates.append(item_id.split("tel:")[-1].strip())
            aria = phone_buttons.nth(i).get_attribute("aria-label") or ""
            if aria.lower().startswith("phone:"):
                candidates.append(aria.split(":", 1)[-1].strip())
            text = phone_buttons.nth(i).inner_text().strip()
            if text:
                candidates.append(text)
        tel_links = page.locator('a[href^="tel:"]')
        for i in range(tel_links.count()):
            href = tel_links.nth(i).get_attribute("href") or ""
            candidates.append(href.replace("tel:", "").strip())
        main = page.locator('[role="main"]')
        if main.count() > 0:
            candidates.extend(PHONE_PATTERN.findall(main.first.inner_text()))
        for raw in candidates:
            phone = normalize_phone(raw)
            digits = re.sub(r"\D", "", phone)
            if len(digits) >= 10:
                return phone
        return ""

    def _extract_email(self, page) -> str:
        candidates = []
        mailto_links = page.locator('a[href^="mailto:"]')
        for i in range(mailto_links.count()):
            href = mailto_links.nth(i).get_attribute("href") or ""
            candidates.append(href.replace("mailto:", "").split("?")[0].strip())
        email_elements = page.locator(
            'button[data-item-id*="email"], a[data-item-id*="email"], '
            'button[aria-label*="Email"], a[aria-label*="Email"]'
        )
        for i in range(email_elements.count()):
            aria = email_elements.nth(i).get_attribute("aria-label") or ""
            candidates.extend(EMAIL_PATTERN.findall(aria))
            item_id = email_elements.nth(i).get_attribute("data-item-id") or ""
            if "mailto:" in item_id:
                candidates.append(item_id.split("mailto:")[-1].strip())
            candidates.extend(EMAIL_PATTERN.findall(item_id))
            text = email_elements.nth(i).inner_text().strip()
            candidates.extend(EMAIL_PATTERN.findall(text))
        main = page.locator('[role="main"]')
        if main.count() > 0:
            candidates.extend(EMAIL_PATTERN.findall(main.first.inner_text()))
        seen = set()
        for raw in candidates:
            email = raw.lower().strip()
            if email in seen:
                continue
            seen.add(email)
            if is_valid_email(email):
                return email
        return ""

    def _extract_email_from_website(self, page, website: str) -> str:
        if not website or not website.startswith("http"):
            return ""
        try:
            page.goto(website, wait_until="domcontentloaded", timeout=WEBSITE_EMAIL_TIMEOUT)
            if self._interruptible_sleep(1.5):
                return ""
            text = page.locator("body").inner_text(timeout=5000)
            for email in EMAIL_PATTERN.findall(text):
                if is_valid_email(email.lower()):
                    return email.lower()
        except Exception:
            pass
        return ""

    def _extract_text_from_button(self, page, item_id: str) -> str:
        button = page.locator(f'button[data-item-id="{item_id}"]')
        if button.count() == 0:
            return ""
        aria = button.first.get_attribute("aria-label") or ""
        if aria:
            return aria.split(":", 1)[-1].strip()
        return button.first.inner_text().strip()

    def _extract_hours(self, page) -> str:
        hours_button = page.locator('button[data-item-id="oh"]')
        if hours_button.count() > 0:
            aria = hours_button.first.get_attribute("aria-label") or ""
            if aria:
                return aria.replace("Hours", "").strip()
        hours_table = page.locator('table[aria-label*="hours"], table[aria-label*="Hours"]')
        if hours_table.count() > 0:
            return " | ".join(
                line.strip() for line in hours_table.first.inner_text().splitlines() if line.strip()
            )
        return ""

    def _extract_business_status(self, page) -> str:
        for text in ("Permanently closed", "Temporarily closed", "Open"):
            if page.locator(f"text={text}").count() > 0:
                return text
        return ""

    def _extract_categories(self, page) -> str:
        category_buttons = page.locator('button[jsaction*="category"]')
        categories = []
        for i in range(min(category_buttons.count(), 5)):
            text = category_buttons.nth(i).inner_text().strip()
            if text and text not in categories:
                categories.append(text)
        return ", ".join(categories)

    def _passes_rating_filter(self, rating: str, reviews: str) -> bool:
        if self.min_rating > 0:
            try:
                if float(rating or 0) < self.min_rating:
                    return False
            except ValueError:
                return False
        if self.min_reviews > 0:
            try:
                if int(reviews or 0) < self.min_reviews:
                    return False
            except ValueError:
                return False
        return True

    def _scrape_place_details(self, page, place_url: str, search_meta: dict) -> dict | None:
        if self.should_stop():
            return None
        page.goto(place_url, wait_until="domcontentloaded", timeout=60000)
        if self._interruptible_sleep(2):
            return None
        name = ""
        heading = page.locator("h1")
        if heading.count() > 0:
            name = heading.first.inner_text().strip()
        address = self._extract_text_from_button(page, "address")
        phone = self._extract_phone(page)
        email = self._extract_email(page)
        website = ""
        website_link = page.locator('a[data-item-id="authority"]')
        if website_link.count() > 0:
            website = website_link.first.get_attribute("href") or ""
        if not email and self.scrape_website_emails and website:
            email = self._extract_email_from_website(page, website)
            page.goto(place_url, wait_until="domcontentloaded", timeout=60000)
        rating = ""
        rating_el = page.locator('div[role="img"][aria-label*="stars"]')
        if rating_el.count() > 0:
            aria = rating_el.first.get_attribute("aria-label") or ""
            match = re.search(r"([\d.]+)", aria)
            if match:
                rating = match.group(1)
        reviews = ""
        reviews_el = page.locator('button[aria-label*="reviews"]')
        if reviews_el.count() > 0:
            aria = reviews_el.first.get_attribute("aria-label") or ""
            match = re.search(r"([\d,]+)", aria)
            if match:
                reviews = match.group(1).replace(",", "")
        if not self._passes_rating_filter(rating, reviews):
            return None
        county = search_meta.get("county") or parse_county_from_address(address)
        return {
            "State": search_meta["state"],
            "City": search_meta["city"],
            "County": county,
            "Category": search_meta["category"],
            "Search Keyword": search_meta["keyword"],
            "Search Latitude": search_meta["search_lat"],
            "Search Longitude": search_meta["search_lng"],
            "Business Name": name,
            "Address": address,
            "Zip Code": parse_zip_code(address),
            "Phone": phone,
            "Email": email,
            "Website": website,
            "Rating": rating,
            "Reviews": reviews,
            "Business Hours": self._extract_hours(page),
            "Business Status": self._extract_business_status(page),
            "Google Categories": self._extract_categories(page),
            "Place URL": place_url,
        }

    def _search_places(self, page, search_meta: dict, seen_urls: set) -> list:
        if self.should_stop():
            return []
        search_url = build_maps_search_url(
            search_meta["keyword"], search_meta["search_lat"], search_meta["search_lng"]
        )
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            self.error(f"Search page failed ({search_meta['city']}, {search_meta['state']}): {exc}")
            return []
        if self._interruptible_sleep(self.delay_between_scrolls + 1.5):
            return []
        self._accept_cookies(page)
        self._scroll_results_feed(page)
        place_urls = self._collect_place_links(page)
        with self._data_lock:
            new_urls = [url for url in place_urls if url not in seen_urls]
        self.log(
            f"  {search_meta['state']} | {search_meta['city']} | "
            f"{search_meta.get('county', '')} | {search_meta['category']} | "
            f"@{search_meta['search_lat']},{search_meta['search_lng']} | "
            f"{len(place_urls)} found, {len(new_urls)} new"
        )
        results = []
        for index, place_url in enumerate(new_urls, start=1):
            if self.should_stop():
                break
            self.log(f"  [{index}/{len(new_urls)}] scraping...")
            try:
                details = self._scrape_place_details(page, place_url, search_meta)
                if details is None:
                    self.log(f"  [{index}/{len(new_urls)}] skipped (rating/reviews filter)")
                    continue
                with self._data_lock:
                    seen_urls.add(place_url)
                results.append(details)
                self.on_record(details)
                if details.get("Phone"):
                    self.log(f"  -> {details['Business Name']}: {details['Phone']}")
            except Exception as exc:
                self.error(f"Place scrape failed: {exc}")
            if self._interruptible_sleep(self.delay_between_leads):
                break
        return results

    def _save_contact_lists(self, df: pd.DataFrame) -> None:
        df = df.copy()
        df["Phone"] = df["Phone"].apply(
            lambda value: normalize_phone(clean_contact_field(value))
        )
        df["Email"] = df["Email"].apply(clean_contact_field)
        phones = df["Phone"].replace("", pd.NA).dropna().drop_duplicates().tolist()
        emails = df["Email"].replace("", pd.NA).dropna().drop_duplicates().tolist()
        self.phones_file.write_text("\n".join(phones), encoding="utf-8")
        self.emails_file.write_text("\n".join(emails), encoding="utf-8")
        contacts = df[(df["Phone"] != "") | (df["Email"] != "")][[
            "Business Name", "Phone", "Email", "Address", "City", "State",
            "Zip Code", "Website", "Rating", "Category",
        ]].drop_duplicates(subset=["Business Name", "Phone", "Email"])
        contacts.to_csv(self.contacts_file, index=False, encoding="utf-8-sig")

    def _save_state_city_files(self, df: pd.DataFrame) -> None:
        for state in df["State"].dropna().unique():
            state_df = df[df["State"] == state]
            safe_state = re.sub(r"[^\w\-]", "_", str(state))
            state_df.to_csv(self.by_state_dir / f"{safe_state}.csv", index=False, encoding="utf-8-sig")
        for city in df["City"].dropna().unique():
            city_df = df[df["City"] == city]
            safe_city = re.sub(r"[^\w\-]", "_", str(city))
            city_df.to_csv(self.by_city_dir / f"{safe_city}.csv", index=False, encoding="utf-8-sig")
        if "County" in df.columns:
            for county in df["County"].dropna().unique():
                if not str(county).strip():
                    continue
                county_df = df[df["County"] == county]
                safe_county = re.sub(r"[^\w\-]", "_", str(county))
                county_df.to_csv(self.by_county_dir / f"{safe_county}.csv", index=False, encoding="utf-8-sig")

    def save_all_data(self, records: list) -> pd.DataFrame:
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.drop_duplicates(subset=["Place URL"], inplace=True)
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        if "Phone" in df.columns:
            df["Phone"] = df["Phone"].apply(
                lambda value: normalize_phone(clean_contact_field(value))
            )
        df = df[CSV_COLUMNS]
        df.to_csv(self.output_file, index=False, encoding="utf-8-sig")
        self._save_contact_lists(df)
        self._save_state_city_files(df)
        return df

    def _record_count(self, final_data: list) -> int:
        return len({r["Place URL"] for r in final_data if r.get("Place URL")})

    def _process_one_search(
        self,
        page,
        search_meta: dict,
        final_data: list,
        seen_urls: set,
        completed: set,
        searches: list,
        resume_index: int,
        index: int,
        pending_len: int,
    ) -> list:
        if self.should_stop():
            return []
        unique_count = self._record_count(final_data)
        if unique_count >= self.target_records:
            return []
        overall_index = resume_index + index
        self.log(
            f"\n[{overall_index}/{len(searches)}] "
            f"{search_meta['query_label']} ({unique_count}/{self.target_records})"
        )
        self.on_progress({
            "total_searches": len(searches),
            "completed_searches": len(completed),
            "pending_searches": pending_len - index + 1,
            "total_records": unique_count,
            "current_state": search_meta["state"],
            "current_city": search_meta["city"],
            "current_county": search_meta.get("county", ""),
            "current_lat": search_meta["search_lat"],
            "current_lng": search_meta["search_lng"],
            "current_category": search_meta["category"],
            "current_keyword": search_meta["keyword"],
            "status": "running",
            "runners": self.runners,
        })
        try:
            results = self._search_places(page, search_meta, seen_urls)
        except Exception as exc:
            self.error(f"Search failed: {exc}")
            results = []
        key = search_key(
            search_meta["state"], search_meta["city"], search_meta["category"],
            search_meta["keyword"], search_meta["search_lat"], search_meta["search_lng"],
        )
        with self._data_lock:
            completed.add(key)
            self._save_completed(completed)
        self._append_history({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "state": search_meta["state"],
            "city": search_meta["city"],
            "county": search_meta.get("county", ""),
            "latitude": search_meta["search_lat"],
            "longitude": search_meta["search_lng"],
            "category": search_meta["category"],
            "keyword": search_meta["keyword"],
            "new_records": len(results),
            "total_records": len(final_data) + len(results),
        })
        if self._interruptible_sleep(self.delay_between_searches):
            return results
        return results

    def _worker_loop(self, worker_id: int, task_queue: Queue, shared: dict) -> None:
        try:
            with sync_playwright() as playwright:
                browser = launch_chromium(playwright, headless=self.headless)
                self.register_browser(browser)
                context = browser.new_context(viewport={"width": 1400, "height": 900}, locale="en-US")
                page = context.new_page()
                while True:
                    if self.should_stop():
                        shared["stopped_early"] = True
                        break
                    item = task_queue.get()
                    if item is None:
                        task_queue.task_done()
                        break
                    if self.should_stop():
                        task_queue.task_done()
                        shared["stopped_early"] = True
                        break
                    search_meta, index = item
                    with self._data_lock:
                        at_target = self._record_count(shared["final_data"]) >= self.target_records
                    if at_target:
                        task_queue.task_done()
                        continue
                    results = self._process_one_search(
                        page, search_meta, shared["final_data"], shared["seen_urls"],
                        shared["completed"], shared["searches"], shared["resume_index"],
                        index, shared["pending_len"],
                    )
                    with self._data_lock:
                        shared["final_data"].extend(results)
                        self._final_data_cache = shared["final_data"]
                        if shared["final_data"]:
                            self.save_all_data(shared["final_data"])
                    task_queue.task_done()
                browser.close()
        except Exception as exc:
            self.error(f"Runner {worker_id} crashed: {exc}")
            shared["stopped_early"] = True

    def run(self) -> dict:
        searches = build_searches(
            self.states, self.businesses, self.search_mode, self.grid_density
        )
        final_data, seen_urls, completed = self._load_records()
        pending, resume_index = self._filter_pending(searches, completed)
        self.log(
            f"Total searches: {len(searches)} | Pending: {len(pending)} | "
            f"Records: {len(final_data)} | Runners: {self.runners} | "
            f"Grid: {self.grid_density}"
        )
        self.on_progress({
            "total_searches": len(searches),
            "completed_searches": len(completed),
            "pending_searches": len(pending),
            "total_records": len(final_data),
            "status": "running",
            "runners": self.runners,
        })
        stopped_early = False

        if self.runners <= 1:
            with sync_playwright() as playwright:
                browser = launch_chromium(playwright, headless=self.headless)
                self.register_browser(browser)
                context = browser.new_context(viewport={"width": 1400, "height": 900}, locale="en-US")
                page = context.new_page()
                for index, search_meta in enumerate(pending, start=1):
                    if self.should_stop():
                        stopped_early = True
                        self.log("Scraping stopped by user.")
                        break
                    if self._record_count(final_data) >= self.target_records:
                        self.log(f"Target reached: {self._record_count(final_data)} records")
                        break
                    results = self._process_one_search(
                        page, search_meta, final_data, seen_urls, completed,
                        searches, resume_index, index, len(pending),
                    )
                    if self.should_stop():
                        stopped_early = True
                        break
                    final_data.extend(results)
                    self._final_data_cache = final_data
                    if final_data:
                        self.save_all_data(final_data)
                try:
                    browser.close()
                except Exception:
                    pass
        else:
            shared = {
                "final_data": final_data,
                "seen_urls": seen_urls,
                "completed": completed,
                "searches": searches,
                "resume_index": resume_index,
                "pending_len": len(pending),
                "stopped_early": False,
            }
            task_queue = Queue()
            for index, search_meta in enumerate(pending, start=1):
                task_queue.put((search_meta, index))
            for _ in range(self.runners):
                task_queue.put(None)
            threads = []
            for worker_id in range(1, self.runners + 1):
                thread = threading.Thread(
                    target=self._worker_loop,
                    args=(worker_id, task_queue, shared),
                    daemon=True,
                )
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
            task_queue.join()
            final_data = shared["final_data"]
            stopped_early = shared["stopped_early"] or self.should_stop()

        self._final_data_cache = final_data
        df = self.save_all_data(final_data) if final_data else pd.DataFrame()
        status = "stopped" if (stopped_early or self.should_stop()) else "completed"
        self.on_progress({
            "total_searches": len(searches),
            "completed_searches": len(completed),
            "pending_searches": max(0, len(searches) - len(completed)),
            "total_records": len(df),
            "status": status,
            "runners": self.runners,
        })
        return {
            "status": status,
            "total_records": len(df),
            "completed_searches": len(completed),
            "total_searches": len(searches),
        }
