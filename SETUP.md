# Setup Guide — Google Map Scrapper

Complete installation and configuration guide for **Google Map Scrapper Web-Based with Python**.

**Developed by [Syed Ahmad Hashmi](https://hashxtech.com)**

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Windows Installation](#windows-installation)
3. [macOS Installation](#macos-installation)
4. [Linux Installation](#linux-installation)
5. [First Run Checklist](#first-run-checklist)
6. [Authentication Setup](#authentication-setup)
7. [Running Your First Scrape](#running-your-first-scrape)
8. [Production / LAN Access](#production--lan-access)
9. [Updating](#updating)
10. [Uninstalling](#uninstalling)

---

## System Requirements

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
- **Google Chrome** — Playwright uses your installed Chrome browser
- **4 GB RAM minimum** — 8 GB recommended for multi-runner jobs
- **Stable internet** — Required for Google Maps and geocoding
- **Disk space** — ~500 MB for dependencies; exports vary by job size

---

## Windows Installation

### Option A — One-click (recommended)

1. Install [Python 3.10+](https://www.python.org/downloads/)
   - Check **"Add Python to PATH"** during installation
2. Install [Google Chrome](https://www.google.com/chrome/)
3. Clone or download this repository
4. Double-click **`start_scraper.bat`**

The script will:
- Verify Python is installed
- Run `python -m app.setup_deps` (pip packages + Playwright Chrome)
- Start the server at http://127.0.0.1:5050
- Open your default browser

### Option B — Manual

```powershell
cd C:\path\to\Google-Map-Scrapper-Web-Based-with-Python

python -m venv venv
venv\Scripts\activate

python -m app.setup_deps
python -m app.web
```

---

## macOS Installation

```bash
# Install Homebrew if needed: https://brew.sh
brew install python@3.12

git clone https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python.git
cd Google-Map-Scrapper-Web-Based-with-Python

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python -m playwright install chrome

python -m app.web
```

Open http://127.0.0.1:5050 in Chrome or Safari.

---

## Linux Installation

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install python3 python3-pip python3-venv

git clone https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python.git
cd Google-Map-Scrapper-Web-Based-with-Python

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python -m playwright install chrome

python -m app.web
```

For headless servers without a display, Playwright still works with `channel="chrome"` if Chrome is installed.

---

## First Run Checklist

After the server starts:

- [ ] Browser opens to http://127.0.0.1:5050
- [ ] `data/` folder is created automatically
- [ ] `data/auth.json` is created on first login attempt
- [ ] Change default login credentials (see below)
- [ ] Create a small test job (one state, Safe speed) before large runs

---

## Authentication Setup

Protected routes (data download, CRM) require login.

### Change credentials

1. Stop the server
2. Edit `data/auth.json`:

```json
{
  "email": "your@email.com",
  "password_hash": "..."
}
```

3. To generate a new password hash, run in Python:

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash("your-new-password"))
```

4. Paste the hash into `password_hash` in `data/auth.json`
5. Restart the server

### Reset credentials

Delete `data/auth.json` and restart. A new file is created with defaults from `app/auth.py`. **Always change these immediately.**

---

## Running Your First Scrape

1. **Login** at `/login` (if accessing protected pages)
2. Go to **New Job** (`/new`)
3. Configure:
   - **Keywords:** e.g. `plumber`, `auto repair shop`
   - **State:** e.g. `Alabama`
   - **Search mode:** `state` (whole state) or `cities` (major cities)
   - **Grid density:** `standard` for most jobs
   - **Speed:** `balanced` (use `safe` if you see blocks)
4. Click **Create**, then **Start**
5. Watch progress on the job page
6. Download CSVs when complete from the job page or `data/exports/`

### Recommended first test

| Setting | Value |
|---------|-------|
| State | Alabama |
| Keywords | `auto repair shop` |
| Grid | Light |
| Speed | Safe |

---

## Production / LAN Access

By default the server binds to `127.0.0.1` (localhost only).

To allow access from other devices on your network:

1. Edit `app/config.py`:
   ```python
   FLASK_HOST = "0.0.0.0"
   FLASK_PORT = 5050
   ```
2. Restart the server
3. Access via `http://<your-ip>:5050`
4. **Use a strong password** in `data/auth.json`
5. Consider a reverse proxy (nginx) with HTTPS for external exposure

> Flask's built-in server is fine for local/LAN use. For heavy production traffic, deploy behind gunicorn + nginx.

---

## Updating

```bash
cd Google-Map-Scrapper-Web-Based-with-Python
git pull origin main
python -m app.setup_deps
```

Your `data/` folder (jobs, exports, credentials) is preserved because it is not in git.

---

## Uninstalling

```bash
# Remove the project folder
rm -rf Google-Map-Scrapper-Web-Based-with-Python

# Optional: remove Playwright browsers
python -m playwright uninstall
```

---

## Getting Help

- **README:** [README.md](README.md) — overview and features
- **Issues:** [GitHub Issues](https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python/issues)
- **Author:** [Syed Ahmad Hashmi — hashxtech.com](https://hashxtech.com)
