# Google Map Scrapper — Web-Based with Python

A web-based Google Maps business scraper with a Flask dashboard, Playwright automation, built-in CRM for lead management, and CSV export. Search businesses by keyword across all 50 US states with configurable grid density and speed presets.

**Developed by [Syed Ahmad Hashmi](https://hashxtech.com)** · [hashxtech.com](https://hashxtech.com)

---

## Features

- **Web dashboard** — Create, start, stop, and monitor scrape jobs from the browser
- **Google Maps scraping** — Business name, phone, email, address, website, rating, hours, and more
- **All 50 US states** — State-wide or city-level search modes with automatic geocoding
- **Grid density** — Light, Standard, Deep, and Ultra coverage to reduce missed businesses
- **Speed presets** — Safe, Balanced, and Fast modes to balance speed vs. block risk
- **Resume support** — Interrupted jobs can be resumed without losing progress
- **CRM module** — Assign, track, comment on, and export leads from scraped data
- **Multiple exports** — `businesses.csv`, `contacts.csv`, `phones.txt`, and per-state/city/county splits
- **Password protection** — Login required to view and download scraped data

---

## Screenshots & Demo

After starting the server, open **http://127.0.0.1:5050** in your browser.

| Page | URL |
|------|-----|
| Dashboard | `/` |
| New scrape job | `/new` |
| CRM | `/crm` |
| Login | `/login` |

---

## Quick Start (Windows)

1. **Install [Python 3.10+](https://www.python.org/downloads/)** and [Google Chrome](https://www.google.com/chrome/)
2. **Clone the repository**
   ```bash
   git clone https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python.git
   cd Google-Map-Scrapper-Web-Based-with-Python
   ```
3. **Double-click `start_scraper.bat`** — installs dependencies, Playwright Chrome, and opens the app

Or run manually:

```bash
python -m app.setup_deps
python -m app.web
```

The server runs at **http://127.0.0.1:5050**.

---

## Quick Start (macOS / Linux)

```bash
git clone https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python.git
cd Google-Map-Scrapper-Web-Based-with-Python

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
python -m playwright install chrome

python -m app.web
```

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or newer |
| Google Chrome | Latest (used by Playwright) |
| OS | Windows, macOS, or Linux |

**Python packages** (installed automatically):

- `flask` — Web server and dashboard
- `playwright` — Browser automation for Google Maps
- `pandas` — CSV export and data handling

---

## Project Structure

```
├── app/
│   ├── web.py            # Flask routes and server
│   ├── scraper_engine.py # Google Maps scraping logic
│   ├── job_manager.py    # Job lifecycle and persistence
│   ├── geocoder.py       # State/city coordinates (OpenStreetMap)
│   ├── crm.py            # Lead management
│   ├── auth.py           # Login protection
│   ├── config.py         # States, presets, settings
│   └── setup_deps.py     # Auto-install dependencies
├── templates/            # HTML pages
├── static/               # CSS and JavaScript
├── data/                 # Runtime data (gitignored)
│   ├── jobs/             # Job configs
│   ├── exports/          # Scraped CSV output
│   ├── coords/           # Cached geocode data
│   └── crm/              # CRM leads
├── archive/legacy/       # Older standalone scripts
├── run.py                # Entry point
├── start_scraper.bat     # Windows one-click launcher
└── requirements.txt
```

---

## How to Use

### 1. Start the server

```bash
python -m app.web
```

### 2. Create a scrape job

1. Go to **New Job** (`/new`)
2. Choose a **business category** preset or enter custom keywords
3. Select a **US state** and search mode (state-wide or cities)
4. Pick **grid density** and **speed preset**
5. Click **Create Job**, then **Start**

### 3. Monitor progress

- Live status, record count, and logs on the job page
- Exports are written to `data/exports/<job_folder>/`

### 4. Download results

| File | Contents |
|------|----------|
| `businesses.csv` | Full business records |
| `contacts.csv` | Name, phone, email, address |
| `phones.txt` | One phone number per line |
| `by_state/` | Records split by state |
| `by_city/` | Records split by city |
| `by_county/` | Records split by county |

### 5. CRM (optional)

Use `/crm` to sync scraped jobs into leads, assign them to team members, add comments, and export filtered CSVs.

---

## Configuration

| Setting | Location | Default |
|---------|----------|---------|
| Server host | `app/config.py` → `FLASK_HOST` | `127.0.0.1` |
| Server port | `app/config.py` → `FLASK_PORT` | `5050` |
| Login credentials | `data/auth.json` (created on first login) | Change after setup |
| Session secret | `data/.session_secret` (auto-generated) | — |

> **Security:** On first run, `data/auth.json` is created automatically. **Change the email and password immediately** before deploying or sharing access.

---

## Development

```bash
# Install in editable/dev mode
pip install -r requirements.txt
python -m playwright install chrome

# Run without auto-opening browser
python -c "from app.web import run_server; run_server(open_browser=False)"

# Legacy CLI scraper (archived)
python google_places_scraper.py
```

### Adding business presets

Edit `BUSINESS_PRESETS` in `app/config.py`:

```python
BUSINESS_PRESETS = {
    "Your Category": [
        "keyword one",
        "keyword two",
    ],
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Python not found` | Install Python 3.10+ and add it to PATH |
| Playwright / Chrome errors | Run `python -m playwright install chrome` |
| No results for a state | Coordinates are fetched on first run via OpenStreetMap — wait and retry |
| Google blocks requests | Switch to **Safe** speed preset; reduce grid density |
| Port 5050 in use | Change `FLASK_PORT` in `app/config.py` |
| Login issues | Delete `data/auth.json` and restart to regenerate credentials |

---

## Legal & Ethical Use

This tool automates publicly visible Google Maps listings for legitimate business research, lead generation, and market analysis. Users are responsible for:

- Complying with [Google's Terms of Service](https://policies.google.com/terms)
- Following applicable data protection laws (GDPR, CCPA, etc.)
- Using scraped data ethically and not for spam or harassment

**Use responsibly. The author is not liable for misuse.**

---

## License

This project is open source and available for public use. See repository settings for license details.

---

## Author

**Syed Ahmad Hashmi**  
Website: [https://hashxtech.com](https://hashxtech.com)  
GitHub: [@smarthashmi](https://github.com/smarthashmi)

---

## Support

For setup help, see [SETUP.md](SETUP.md).

Found a bug or want a feature? [Open an issue](https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python/issues).
