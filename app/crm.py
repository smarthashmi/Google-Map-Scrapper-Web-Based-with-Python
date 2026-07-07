"""Local JSON CRM for scraped leads — assign, comment, export."""

import csv
import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.config import CRM_DIR, EXPORTS_DIR
from app.job_manager import job_manager

CRM_FILE = CRM_DIR / "leads.json"
EXPORTS_CRM_DIR = CRM_DIR / "exports"
_lock = threading.Lock()

CRM_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_CRM_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _lead_id(place_url: str, phone: str, business_name: str) -> str:
    raw = f"{place_url}|{phone}|{business_name}".strip().lower()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _load() -> dict:
    if CRM_FILE.exists():
        return json.loads(CRM_FILE.read_text(encoding="utf-8"))
    return {"leads": {}, "meta": {"last_sync": None}}


def _save(data: dict) -> None:
    CRM_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _row_to_lead(row: dict, job_id: str, job_name: str) -> dict:
    place_url = str(row.get("Place URL", "") or "")
    phone = str(row.get("Phone", "") or "")
    name = str(row.get("Business Name", "") or "")
    lid = _lead_id(place_url, phone, name)
    return {
        "id": lid,
        "job_id": job_id,
        "job_name": job_name,
        "business_name": name,
        "phone": phone,
        "email": str(row.get("Email", "") or ""),
        "address": str(row.get("Address", "") or ""),
        "city": str(row.get("City", "") or ""),
        "county": str(row.get("County", "") or ""),
        "state": str(row.get("State", "") or ""),
        "category": str(row.get("Category", "") or ""),
        "rating": str(row.get("Rating", "") or ""),
        "reviews": str(row.get("Reviews", "") or ""),
        "website": str(row.get("Website", "") or ""),
        "place_url": place_url,
        "status": "available",
        "assigned_to": "",
        "comment": "",
        "assigned_at": "",
        "exported_at": "",
        "updated_at": _now(),
        "created_at": _now(),
    }


def sync_all_jobs() -> dict:
    """Import new records from all job CSV files into CRM."""
    with _lock:
        data = _load()
        leads = data.get("leads", {})
        added = 0
        for job in job_manager.list_jobs():
            job_id = job["id"]
            csv_path = Path(job.get("export_dir", "")) / "businesses.csv"
            if not csv_path.exists():
                csv_path = EXPORTS_DIR / job_id / "businesses.csv"
            if not csv_path.exists():
                continue
            try:
                df = pd.read_csv(csv_path)
            except Exception:
                continue
            for row in df.fillna("").to_dict("records"):
                lead = _row_to_lead(row, job_id, job.get("name", job_id))
                if lead["id"] not in leads:
                    leads[lead["id"]] = lead
                    added += 1
                elif leads[lead["id"]].get("status") == "deleted":
                    pass
                else:
                    existing = leads[lead["id"]]
                    for key in ("phone", "email", "address", "rating", "reviews", "website"):
                        if lead.get(key) and not existing.get(key):
                            existing[key] = lead[key]
        data["leads"] = leads
        data["meta"] = {"last_sync": _now(), "total": len(leads)}
        _save(data)
        return {"added": added, "total": len(leads)}


def get_stats() -> dict:
    sync_all_jobs()
    data = _load()
    leads = list(data.get("leads", {}).values())
    active = [l for l in leads if l.get("status") != "deleted"]
    return {
        "total": len(active),
        "available": sum(1 for l in active if l.get("status") == "available"),
        "assigned": sum(1 for l in active if l.get("status") == "assigned"),
        "exported": sum(1 for l in active if l.get("status") == "exported"),
        "last_sync": data.get("meta", {}).get("last_sync"),
    }


def get_job_summaries() -> list[dict]:
    sync_all_jobs()
    data = _load()
    leads = [l for l in data.get("leads", {}).values() if l.get("status") != "deleted"]
    jobs = job_manager.list_jobs()
    summaries = []
    for job in jobs:
        job_leads = [l for l in leads if l.get("job_id") == job["id"]]
        export_dir = Path(job.get("export_dir", ""))
        files = []
        if export_dir.exists():
            for fname in ("businesses.csv", "contacts.csv", "phones.txt", "emails.txt"):
                if (export_dir / fname).exists():
                    files.append(fname)
        summaries.append({
            "job": job,
            "total": len(job_leads),
            "available": sum(1 for l in job_leads if l.get("status") == "available"),
            "assigned": sum(1 for l in job_leads if l.get("status") == "assigned"),
            "exported": sum(1 for l in job_leads if l.get("status") == "exported"),
            "files": files,
            "export_dir": str(export_dir),
        })
    return summaries


def list_leads(
    status: str = "all",
    job_id: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    data = _load()
    leads = [l for l in data.get("leads", {}).values() if l.get("status") != "deleted"]
    if job_id:
        leads = [l for l in leads if l.get("job_id") == job_id]
    if status and status != "all":
        leads = [l for l in leads if l.get("status") == status]
    leads.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    total = len(leads)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    return {
        "leads": leads[start:start + per_page],
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
    }


def pick_available(quantity: int, job_id: str | None = None) -> list[dict]:
    data = _load()
    available = [
        l for l in data.get("leads", {}).values()
        if l.get("status") == "available"
    ]
    if job_id:
        available = [l for l in available if l.get("job_id") == job_id]
    available.sort(key=lambda x: x.get("created_at", ""))
    return available[: max(0, int(quantity))]


def assign_leads(lead_ids: list[str], assigned_to: str, comment: str = "") -> dict:
    with _lock:
        data = _load()
        leads = data.get("leads", {})
        updated = 0
        for lid in lead_ids:
            if lid not in leads or leads[lid].get("status") == "deleted":
                continue
            leads[lid]["status"] = "assigned"
            leads[lid]["assigned_to"] = assigned_to.strip()
            leads[lid]["comment"] = comment.strip()
            leads[lid]["assigned_at"] = _now()
            leads[lid]["updated_at"] = _now()
            updated += 1
        _save(data)
        return {"updated": updated}


def update_lead(lead_id: str, comment: str = None, assigned_to: str = None, status: str = None) -> dict:
    with _lock:
        data = _load()
        leads = data.get("leads", {})
        if lead_id not in leads:
            return {"ok": False, "error": "Lead not found"}
        lead = leads[lead_id]
        if comment is not None:
            lead["comment"] = comment.strip()
        if assigned_to is not None:
            lead["assigned_to"] = assigned_to.strip()
        if status is not None:
            lead["status"] = status
            if status == "assigned" and not lead.get("assigned_at"):
                lead["assigned_at"] = _now()
        lead["updated_at"] = _now()
        _save(data)
        return {"ok": True, "lead": lead}


def delete_leads(lead_ids: list[str]) -> dict:
    with _lock:
        data = _load()
        leads = data.get("leads", {})
        for lid in lead_ids:
            if lid in leads:
                leads[lid]["status"] = "deleted"
                leads[lid]["updated_at"] = _now()
        _save(data)
        return {"deleted": len(lead_ids)}


def release_leads(lead_ids: list[str]) -> dict:
    with _lock:
        data = _load()
        leads = data.get("leads", {})
        for lid in lead_ids:
            if lid in leads:
                leads[lid]["status"] = "available"
                leads[lid]["assigned_to"] = ""
                leads[lid]["assigned_at"] = ""
                leads[lid]["updated_at"] = _now()
        _save(data)
        return {"released": len(lead_ids)}


def export_leads_csv(lead_ids: list[str], label: str = "export") -> Path:
    with _lock:
        data = _load()
        leads = data.get("leads", {})
        rows = []
        for lid in lead_ids:
            if lid in leads and leads[lid].get("status") != "deleted":
                rows.append(leads[lid])
                leads[lid]["status"] = "exported"
                leads[lid]["exported_at"] = _now()
                leads[lid]["updated_at"] = _now()
        _save(data)

    if not rows:
        raise ValueError("No leads to export")

    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
    filename = f"{datetime.now().strftime('%Y-%m-%d')}_{safe_label}_{len(rows)}leads.csv"
    out_path = EXPORTS_CRM_DIR / filename
    fields = [
        "business_name", "phone", "email", "address", "city", "county", "state",
        "category", "rating", "reviews", "website", "job_name", "status",
        "assigned_to", "comment", "assigned_at", "place_url",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return out_path
