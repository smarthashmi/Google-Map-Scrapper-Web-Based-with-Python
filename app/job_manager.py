"""Job lifecycle: create, run, pause, resume, history."""

import json
import re
import threading
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.config import EXPORTS_DIR, JOBS_DIR
from app.scraper_engine import ScraperEngine


class JobManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._stop_flags: dict[str, threading.Event] = {}
        self._engines: dict[str, ScraperEngine] = {}
        self._live_logs: dict[str, deque] = {}
        self._live_errors: dict[str, deque] = {}
        self._live_records: dict[str, deque] = {}
        self._live_progress: dict[str, dict] = {}

    def _job_meta_path(self, job_id: str) -> Path:
        return JOBS_DIR / f"{job_id}.json"

    def _export_dir(self, job_id: str) -> Path:
        meta = self.get_job(job_id)
        if meta and meta.get("export_dir"):
            return Path(meta["export_dir"])
        return EXPORTS_DIR / job_id

    def list_jobs(self) -> list[dict]:
        jobs = []
        for path in sorted(JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                job_id = job.get("id", path.stem)
                if self.is_running(job_id):
                    job["live_status"] = "running"
                else:
                    job["live_status"] = self._live_progress.get(job_id, {}).get("status", job.get("status"))
                job["record_count"] = self.get_record_count(job_id)
                jobs.append(job)
            except Exception:
                continue
        return jobs

    def get_job(self, job_id: str) -> dict | None:
        path = self._job_meta_path(job_id)
        if not path.exists():
            return None
        job = json.loads(path.read_text(encoding="utf-8"))
        if job.get("status") == "running" and not self.is_running(job_id):
            job["status"] = "stopped"
            self._save_job(job)
        job["live_progress"] = self._live_progress.get(job_id, job.get("progress", {}))
        return job

    def _save_job(self, job: dict) -> None:
        path = self._job_meta_path(job["id"])
        path.write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^\w\-]+", "_", text.strip().lower()).strip("_")[:40]

    def create_job(
        self,
        name: str,
        businesses: list[dict],
        states: list[str],
        target_records: int = 10000,
        search_mode: str = "state",
        grid_density: str = "standard",
        scrape_website_emails: bool = False,
        headless: bool = True,
        min_rating: float = 0,
        min_reviews: int = 0,
        runners: int = 2,
        speed_preset: str = "balanced",
        delay_between_leads: float = 1.5,
        delay_between_searches: float = 3.0,
        delay_between_scrolls: float = 1.5,
    ) -> dict:
        job_id = str(uuid.uuid4())[:8]
        date_str = datetime.now().strftime("%Y-%m-%d")
        biz_slug = self._slugify(businesses[0]["name"] if businesses else "scrape")
        states_slug = self._slugify("_".join(states[:3]))
        folder_name = f"{date_str}_{biz_slug}_{states_slug}_{job_id}"
        export_dir = EXPORTS_DIR / folder_name
        export_dir.mkdir(parents=True, exist_ok=True)

        job = {
            "id": job_id,
            "name": name or folder_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "ready",
            "businesses": businesses,
            "states": states,
            "target_records": target_records,
            "search_mode": search_mode,
            "grid_density": grid_density,
            "scrape_website_emails": scrape_website_emails,
            "headless": headless,
            "min_rating": min_rating,
            "min_reviews": min_reviews,
            "runners": max(1, min(4, int(runners))),
            "speed_preset": speed_preset,
            "delay_between_leads": delay_between_leads,
            "delay_between_searches": delay_between_searches,
            "delay_between_scrolls": delay_between_scrolls,
            "export_dir": str(export_dir),
            "progress": {},
            "error": None,
        }
        (export_dir / "job_config.json").write_text(
            json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self._save_job(job)
        self._live_logs[job_id] = deque(maxlen=300)
        self._live_errors[job_id] = deque(maxlen=100)
        self._live_records[job_id] = deque(maxlen=50)
        return job

    def get_logs(self, job_id: str) -> list[str]:
        return list(self._live_logs.get(job_id, deque()))

    def get_errors(self, job_id: str) -> list[str]:
        return list(self._live_errors.get(job_id, deque()))

    def get_live_records(self, job_id: str) -> list[dict]:
        return list(self._live_records.get(job_id, deque()))

    def get_record_count(self, job_id: str) -> int:
        export_dir = self._export_dir(job_id)
        csv_file = export_dir / "businesses.csv"
        if not csv_file.exists():
            return 0
        try:
            df = pd.read_csv(csv_file)
            return len(df)
        except Exception:
            return 0

    def get_scraped_records(self, job_id: str, page: int = 1, per_page: int = 50) -> dict:
        export_dir = self._export_dir(job_id)
        csv_file = export_dir / "businesses.csv"
        if not csv_file.exists():
            return {"records": [], "total": 0, "page": page, "per_page": per_page, "pages": 0}
        df = pd.read_csv(csv_file)
        total = len(df)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        chunk = df.iloc[start:start + per_page]
        return {
            "records": chunk.fillna("").to_dict("records"),
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    def get_all_records_preview(self, page: int = 1, per_page: int = 50) -> dict:
        jobs = sorted(self.list_jobs(), key=lambda j: j.get("record_count", 0), reverse=True)
        all_records = []
        for job in jobs:
            if job.get("record_count", 0) == 0:
                continue
            data = self.get_scraped_records(job["id"], page=1, per_page=10000)
            for row in data["records"]:
                row["job_name"] = job.get("name", "")
                row["job_id"] = job.get("id", "")
                all_records.append(row)
        total = len(all_records)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        return {
            "records": all_records[start:start + per_page],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    def is_running(self, job_id: str) -> bool:
        thread = self._threads.get(job_id)
        return thread is not None and thread.is_alive()

    def start_job(self, job_id: str) -> dict:
        job = self.get_job(job_id)
        if not job:
            return {"ok": False, "error": "Job not found"}
        if self.is_running(job_id):
            return {"ok": False, "error": "Job is already running"}

        stop_event = threading.Event()
        self._stop_flags[job_id] = stop_event
        if job_id not in self._live_logs:
            self._live_logs[job_id] = deque(maxlen=300)
        if job_id not in self._live_errors:
            self._live_errors[job_id] = deque(maxlen=100)
        if job_id not in self._live_records:
            self._live_records[job_id] = deque(maxlen=50)

        def run_worker():
            try:
                job["status"] = "running"
                job["updated_at"] = datetime.now().isoformat()
                self._save_job(job)

                def on_log(msg):
                    self._live_logs[job_id].append(msg)

                def on_error(msg):
                    self._live_errors[job_id].append(
                        f"{datetime.now().strftime('%H:%M:%S')} — {msg}"
                    )

                def on_record(record):
                    self._live_records[job_id].append({
                        "name": record.get("Business Name", ""),
                        "phone": record.get("Phone", ""),
                        "email": record.get("Email", ""),
                        "city": record.get("City", ""),
                        "county": record.get("County", ""),
                        "state": record.get("State", ""),
                        "rating": record.get("Rating", ""),
                        "reviews": record.get("Reviews", ""),
                        "category": record.get("Category", ""),
                        "lat": record.get("Search Latitude", ""),
                        "lng": record.get("Search Longitude", ""),
                    })

                def on_progress(data):
                    if stop_event.is_set():
                        data["status"] = "stopped"
                    self._live_progress[job_id] = data
                    job["progress"] = data
                    job["status"] = data.get("status", "running")
                    job["updated_at"] = datetime.now().isoformat()
                    self._save_job(job)

                engine = ScraperEngine(
                    job_dir=Path(job["export_dir"]),
                    states=job["states"],
                    businesses=job["businesses"],
                    target_records=job["target_records"],
                    search_mode=job["search_mode"],
                    grid_density=job.get("grid_density", "standard"),
                    scrape_website_emails=job.get("scrape_website_emails", False),
                    headless=job["headless"],
                    min_rating=job.get("min_rating", 0),
                    min_reviews=job.get("min_reviews", 0),
                    runners=job.get("runners", 1),
                    delay_between_leads=job.get("delay_between_leads", 1.5),
                    delay_between_searches=job.get("delay_between_searches", 3.0),
                    delay_between_scrolls=job.get("delay_between_scrolls", 1.5),
                    on_log=on_log,
                    on_error=on_error,
                    on_record=on_record,
                    on_progress=on_progress,
                    should_stop=stop_event.is_set,
                )
                self._engines[job_id] = engine
                result = engine.run()
                if stop_event.is_set():
                    result["status"] = "stopped"
                job["status"] = result["status"]
                job["progress"] = self._live_progress.get(job_id, {})
                job["updated_at"] = datetime.now().isoformat()
                self._save_job(job)
            except Exception as exc:
                job["status"] = "error"
                job["error"] = str(exc)
                job["updated_at"] = datetime.now().isoformat()
                self._save_job(job)
                self._live_logs[job_id].append(f"ERROR: {exc}")
                self._live_errors[job_id].append(
                    f"{datetime.now().strftime('%H:%M:%S')} — {exc}"
                )
            finally:
                self._threads.pop(job_id, None)
                self._engines.pop(job_id, None)
                self._stop_flags.pop(job_id, None)

        thread = threading.Thread(target=run_worker, daemon=True)
        self._threads[job_id] = thread
        thread.start()
        return {"ok": True}

    def stop_job(self, job_id: str) -> dict:
        running = self.is_running(job_id)
        if not running and job_id not in self._stop_flags:
            job = self.get_job(job_id)
            if not job or job.get("status") not in ("running", "ready"):
                return {"ok": False, "error": "Job is not running"}

        if job_id in self._stop_flags:
            self._stop_flags[job_id].set()

        engine = self._engines.get(job_id)
        if engine:
            engine.force_stop()
            self._live_logs.setdefault(job_id, deque()).append("Stop requested — saving data and closing browser...")

        job = self.get_job(job_id)
        if job:
            job["status"] = "stopped"
            progress = job.get("progress", {})
            progress["status"] = "stopped"
            job["progress"] = progress
            job["updated_at"] = datetime.now().isoformat()
            self._live_progress[job_id] = progress
            self._save_job(job)

        return {"ok": True, "message": "Scraping stopped", "stopping": running}

    def resume_job(self, job_id: str) -> dict:
        job = self.get_job(job_id)
        if not job:
            return {"ok": False, "error": "Job not found"}
        if self.is_running(job_id):
            return {"ok": False, "error": "Job is already running"}
        progress = job.get("progress", {})
        pending = progress.get("pending_searches", 1)
        if job.get("status") == "completed" and pending == 0:
            return {"ok": False, "error": "Job already completed — all searches done"}
        return self.start_job(job_id)

    def get_history(self, job_id: str) -> list:
        export_dir = self._export_dir(job_id)
        history_file = export_dir / "history.json"
        if history_file.exists():
            return json.loads(history_file.read_text(encoding="utf-8"))
        return []

    def delete_job(self, job_id: str) -> dict:
        if self.is_running(job_id):
            return {"ok": False, "error": "Stop the job before deleting"}
        meta_path = self._job_meta_path(job_id)
        if meta_path.exists():
            meta_path.unlink()
        self._live_logs.pop(job_id, None)
        self._live_errors.pop(job_id, None)
        self._live_records.pop(job_id, None)
        self._live_progress.pop(job_id, None)
        self._engines.pop(job_id, None)
        self._stop_flags.pop(job_id, None)
        return {"ok": True}


job_manager = JobManager()
