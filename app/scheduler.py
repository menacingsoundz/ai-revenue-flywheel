"""Scheduler: Mon–Fri + weekend jobs from config/schedules.json.
Dedupe by job+day, retry max 3 with backoff, errors logged, recovery = log + continue."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import db
from app.agents import AGENTS

CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "schedules.json")

JOBS = {
    "monday_research": [("research", "research"), ("research", "ideas"), ("executive", "review")],
    "tuesday_build": [("product_creation", "build_products"), ("quality_control", "qc_all")],
    "wednesday_marketing": [("marketing", "generate_content"), ("distribution", "build_queue")],
    "thursday_acquisition": [("optimization", "optimize"), ("marketing", "generate_content")],
    "friday_finance": [("financial", "financial_report"), ("optimization", "optimize"), ("executive", "review")],
    "weekend_maintenance": [("executive", "review"), ("financial", "financial_report")],
}

def load_config():
    with open(CONFIG) as f: return json.load(f)

def run_job(job_id, max_retries=3):
    if job_id not in JOBS:
        db.log_error("scheduler", f"Unknown job: {job_id}")
        return {"job": job_id, "status": "failed", "error": "unknown job"}
    # dedupe: same job already ok today?
    from datetime import date
    today = date.today().isoformat()
    c = db.connect()
    done = c.execute("SELECT id FROM agent_runs WHERE job=? AND status='ok' AND substr(started_at,1,10)=?",
                     (job_id, today)).fetchone()
    c.close()
    if done:
        return {"job": job_id, "status": "skipped_duplicate", "note": "Already ran successfully today."}
    results = []
    for agent_name, task in JOBS[job_id]:
        agent = AGENTS[agent_name]
        if agent.status == "disabled":
            results.append({"agent": agent_name, "status": "skipped_disabled"}); continue
        attempt = 0
        while True:
            try:
                r = agent.run(job_id)
                results.append(r); break
            except Exception as e:  # noqa: BLE001 - retry then log, never crash the cycle
                attempt += 1
                if attempt >= max_retries:
                    db.log_error("scheduler", f"{job_id}/{agent_name} failed after {max_retries} attempts: {e}")
                    results.append({"agent": agent_name, "status": "failed", "error": str(e)}); break
                time.sleep(2 ** attempt)
    ok = all(r.get("status") in ("ok", "not_operational", "skipped_disabled") for r in results)
    db.log_activity("scheduler", f"job {job_id}", "ok" if ok else "partial failure")
    return {"job": job_id, "status": "ok" if ok else "partial", "results": results}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--run", required=True); p.add_argument("--list", action="store_true")
    a = p.parse_args()
    if a.list:
        print(json.dumps(load_config(), indent=2)); sys.exit(0)
    db.init_db()
    print(json.dumps(run_job(a.run), indent=2, default=str))
