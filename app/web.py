"""Flask web application for business scraper."""

import secrets
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from app.auth import is_authenticated, login_required, login_required_api, verify_login
from app.config import BASE_DIR, BUSINESS_PRESETS, CRM_DIR, EXPORTS_DIR, FLASK_HOST, FLASK_PORT, GRID_DENSITY, SPEED_PRESETS, US_STATES
from app.crm import (
    assign_leads,
    delete_leads,
    export_leads_csv,
    get_job_summaries,
    get_stats,
    list_leads,
    pick_available,
    release_leads,
    sync_all_jobs,
    update_lead,
)
from app.job_manager import job_manager

SECRET_FILE = BASE_DIR / "data" / ".session_secret"


def _load_secret_key() -> str:
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    SECRET_FILE.write_text(key, encoding="utf-8")
    return key


app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = _load_secret_key()


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return redirect(request.args.get("next") or url_for("dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        next_url = request.form.get("next") or request.args.get("next")
        if verify_login(email, password):
            session["authenticated"] = True
            session["email"] = email.strip().lower()
            session.permanent = True
            app.permanent_session_lifetime = 86400 * 7
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("crm_dashboard"))
        error = "Invalid email or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


@app.route("/")
def dashboard():
    jobs = job_manager.list_jobs()
    return render_template("dashboard.html", jobs=jobs, authenticated=is_authenticated())


@app.route("/crm")
@login_required
def crm_dashboard():
    stats = get_stats()
    summaries = get_job_summaries()
    return render_template("crm_dashboard.html", stats=stats, summaries=summaries)


@app.route("/crm/leads")
@login_required
def crm_leads():
    job_id = request.args.get("job_id") or None
    status = request.args.get("status", "available")
    page = int(request.args.get("page", 1))
    data = list_leads(status=status, job_id=job_id, page=page, per_page=50)
    jobs = [s["job"] for s in get_job_summaries()]
    stats = get_stats()
    return render_template(
        "crm_leads.html",
        data=data,
        jobs=jobs,
        stats=stats,
        filter_status=status,
        filter_job_id=job_id or "",
    )


@app.route("/api/crm/sync", methods=["POST"])
@login_required_api
def api_crm_sync():
    result = sync_all_jobs()
    return jsonify({"ok": True, **result, "stats": get_stats()})


@app.route("/api/crm/pick", methods=["POST"])
@login_required_api
def api_crm_pick():
    body = request.get_json(force=True)
    quantity = int(body.get("quantity", 10))
    job_id = body.get("job_id") or None
    leads = pick_available(quantity, job_id)
    return jsonify({"ok": True, "leads": leads, "count": len(leads)})


@app.route("/api/crm/assign", methods=["POST"])
@login_required_api
def api_crm_assign():
    body = request.get_json(force=True)
    lead_ids = body.get("lead_ids", [])
    assigned_to = body.get("assigned_to", session.get("email", "User"))
    comment = body.get("comment", "")
    if not lead_ids:
        return jsonify({"ok": False, "error": "No leads selected"}), 400
    result = assign_leads(lead_ids, assigned_to, comment)
    return jsonify({"ok": True, **result})


@app.route("/api/crm/release", methods=["POST"])
@login_required_api
def api_crm_release():
    body = request.get_json(force=True)
    lead_ids = body.get("lead_ids", [])
    result = release_leads(lead_ids)
    return jsonify({"ok": True, **result})


@app.route("/api/crm/delete", methods=["POST"])
@login_required_api
def api_crm_delete():
    body = request.get_json(force=True)
    lead_ids = body.get("lead_ids", [])
    result = delete_leads(lead_ids)
    return jsonify({"ok": True, **result})


@app.route("/api/crm/comment", methods=["POST"])
@login_required_api
def api_crm_comment():
    body = request.get_json(force=True)
    lead_id = body.get("lead_id")
    comment = body.get("comment", "")
    assigned_to = body.get("assigned_to")
    return jsonify(update_lead(lead_id, comment=comment, assigned_to=assigned_to))


@app.route("/api/crm/export", methods=["POST"])
@login_required_api
def api_crm_export():
    body = request.get_json(force=True)
    lead_ids = body.get("lead_ids", [])
    label = body.get("label", "assigned_export")
    if not lead_ids:
        return jsonify({"ok": False, "error": "No leads selected"}), 400
    try:
        path = export_leads_csv(lead_ids, label)
        return jsonify({"ok": True, "filename": path.name, "count": len(lead_ids)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/crm/download/<filename>")
@login_required
def crm_download_export(filename):
    safe = Path(filename).name
    path = CRM_DIR / "exports" / safe
    if not path.exists():
        return "Not found", 404
    return send_from_directory(path.parent, path.name, as_attachment=True)


@app.route("/new")
def new_job_wizard():
    step = int(request.args.get("step", 1))
    return render_template(
        "wizard.html",
        step=step,
        presets=BUSINESS_PRESETS,
        states=US_STATES,
        speed_presets=SPEED_PRESETS,
        grid_densities=GRID_DENSITY,
    )


@app.route("/job/<job_id>")
def job_detail(job_id):
    job = job_manager.get_job(job_id)
    if not job:
        return redirect(url_for("dashboard"))
    history = job_manager.get_history(job_id)
    job["record_count"] = job_manager.get_record_count(job_id)
    return render_template(
        "job.html",
        job=job,
        history=history[-50:],
        authenticated=is_authenticated(),
    )


@app.route("/job/<job_id>/data")
@login_required
def job_data(job_id):
    job = job_manager.get_job(job_id)
    if not job:
        return redirect(url_for("dashboard"))
    page = int(request.args.get("page", 1))
    data = job_manager.get_scraped_records(job_id, page=page, per_page=50)
    return render_template("data.html", job=job, data=data, scope="job")


@app.route("/data/all")
@login_required
def all_data():
    page = int(request.args.get("page", 1))
    data = job_manager.get_all_records_preview(page=page, per_page=50)
    return render_template("data.html", job=None, data=data, scope="all")


@app.route("/api/jobs", methods=["POST"])
def api_create_job():
    data = request.get_json(force=True)
    businesses = data.get("businesses", [])
    states = data.get("states", [])

    if not businesses:
        return jsonify({"ok": False, "error": "Add at least one business type"}), 400
    if not states:
        return jsonify({"ok": False, "error": "Select at least one state"}), 400

    job = job_manager.create_job(
        name=data.get("name", ""),
        businesses=businesses,
        states=states,
        target_records=int(data.get("target_records", 10000)),
        search_mode=data.get("search_mode", "state"),
        grid_density=data.get("grid_density", "standard"),
        scrape_website_emails=bool(data.get("scrape_website_emails", False)),
        headless=bool(data.get("headless", True)),
        min_rating=float(data.get("min_rating", 0)),
        min_reviews=int(data.get("min_reviews", 0)),
        runners=int(data.get("runners", 2)),
        speed_preset=data.get("speed_preset", "balanced"),
        delay_between_leads=float(data.get("delay_between_leads", 1.5)),
        delay_between_searches=float(data.get("delay_between_searches", 3.0)),
        delay_between_scrolls=float(data.get("delay_between_scrolls", 1.5)),
    )
    return jsonify({"ok": True, "job": job})


@app.route("/api/jobs/<job_id>/start", methods=["POST"])
def api_start_job(job_id):
    return jsonify(job_manager.start_job(job_id))


@app.route("/api/jobs/<job_id>/stop", methods=["POST"])
def api_stop_job(job_id):
    return jsonify(job_manager.stop_job(job_id))


@app.route("/api/jobs/<job_id>/resume", methods=["POST"])
def api_resume_job(job_id):
    return jsonify(job_manager.resume_job(job_id))


@app.route("/api/jobs/<job_id>/status")
def api_job_status(job_id):
    job = job_manager.get_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Not found"}), 404
    running = job_manager.is_running(job_id)
    if running:
        job["status"] = "running"
    logs = job_manager.get_logs(job_id)[-40:]
    errors = job_manager.get_errors(job_id)[-20:]
    records = job_manager.get_live_records(job_id)[-25:]
    return jsonify({
        "ok": True,
        "job": job,
        "logs": logs,
        "errors": errors,
        "live_records": records,
        "running": running,
        "record_count": job_manager.get_record_count(job_id),
        "history": job_manager.get_history(job_id)[-20:],
    })


@app.route("/api/jobs/<job_id>/records")
@login_required_api
def api_job_records(job_id):
    page = int(request.args.get("page", 1))
    return jsonify({"ok": True, **job_manager.get_scraped_records(job_id, page=page)})


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def api_delete_job(job_id):
    return jsonify(job_manager.delete_job(job_id))


@app.route("/download/<job_id>/<path:filename>")
@login_required
def download_file(job_id, filename):
    job = job_manager.get_job(job_id)
    if not job:
        return "Not found", 404
    export_dir = Path(job["export_dir"])
    safe_path = (export_dir / filename).resolve()
    if not str(safe_path).startswith(str(export_dir.resolve())):
        return "Forbidden", 403
    if not safe_path.exists():
        return "Not found", 404
    return send_from_directory(safe_path.parent, safe_path.name, as_attachment=True)


@app.route("/api/presets")
def api_presets():
    return jsonify(BUSINESS_PRESETS)


def create_app():
    return app


def run_server(open_browser: bool = True):
    from app.setup_deps import ensure_all

    ensure_all()

    if open_browser:
        import threading
        import webbrowser

        def open_browser_delayed():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{FLASK_HOST}:{FLASK_PORT}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    run_server(open_browser=True)
