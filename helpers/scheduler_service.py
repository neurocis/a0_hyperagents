from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
from usr.plugins.a0_hyperagents.helpers.common import append_jsonl, human_table, now_iso, path_in_plugin_storage, read_jsonl, write_json, new_id


def jobs_path(agent=None) -> Path:
    return path_in_plugin_storage("jobs.jsonl", agent=agent)


def _parse_iso(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _next_run_from_schedule(schedule: dict) -> str | None:
    now = datetime.now(timezone.utc)
    kind = (schedule or {}).get("type") or (schedule or {}).get("kind")
    if kind == "interval":
        sec = int((schedule or {}).get("every_seconds", 3600))
        return (now + timedelta(seconds=sec)).isoformat()
    if kind == "once":
        return (schedule or {}).get("run_at") or now.isoformat()
    if kind == "cron":
        # MVP: cron parsing is intentionally not implemented; schedule for one hour out.
        return (now + timedelta(hours=1)).isoformat()
    return now.isoformat()


def list_jobs(agent=None, include_cancelled: bool = False) -> list[dict]:
    rows = read_jsonl(jobs_path(agent))
    latest = {}
    for r in rows:
        jid = r.get("id")
        if jid:
            latest[jid] = r
    jobs = list(latest.values())
    if not include_cancelled:
        jobs = [j for j in jobs if j.get("state") != "cancelled"]
    return jobs


def create_job(job: dict, agent=None) -> dict:
    job = dict(job or {})
    job.setdefault("id", new_id("job"))
    job.setdefault("created_at", now_iso())
    job.setdefault("state", "active")
    job.setdefault("attempts", 0)
    job.setdefault("next_run_at", _next_run_from_schedule(job.get("schedule") or {"type": "once"}))
    append_jsonl(jobs_path(agent), job)
    return job


def update_job(job_id: str, updates: dict, agent=None) -> dict:
    job = get_job(job_id, agent=agent) or {"id": job_id, "created_at": now_iso()}
    job.update(updates or {})
    job["updated_at"] = now_iso()
    append_jsonl(jobs_path(agent), job)
    return job


def get_job(job_id: str, agent=None) -> dict | None:
    for j in reversed(read_jsonl(jobs_path(agent))):
        if j.get("id") == job_id:
            return j
    return None


def cancel_job(job_id: str, agent=None) -> dict:
    return update_job(job_id, {"state": "cancelled", "cancelled_at": now_iso()}, agent=agent)


def due_jobs(agent=None) -> list[dict]:
    now = datetime.now(timezone.utc)
    out = []
    for j in list_jobs(agent=agent):
        if j.get("state") != "active":
            continue
        dt = _parse_iso(j.get("next_run_at", ""))
        if dt is None or dt <= now:
            out.append(j)
    return out


def mark_job_result(job_id: str, result: dict, agent=None) -> dict:
    job = get_job(job_id, agent=agent) or {"id": job_id}
    job["last_result"] = result
    job["last_run_at"] = now_iso()
    job["attempts"] = int(job.get("attempts", 0)) + 1
    if job.get("kind") == "recurring" or (job.get("schedule") or {}).get("type") in {"interval", "cron"}:
        job["next_run_at"] = _next_run_from_schedule(job.get("schedule") or {})
        job["state"] = "active"
    else:
        job["state"] = "completed" if result.get("ok", True) else "failed"
    append_jsonl(jobs_path(agent), job)
    return job


def run_due_jobs(agent=None) -> dict:
    # MVP does not proactively instantiate AgentContext. It returns due jobs and marks them observed.
    jobs = due_jobs(agent=agent)
    observed = []
    for j in jobs:
        observed.append(mark_job_result(j["id"], {"ok": True, "message": "Due job observed by hyperagents scheduler MVP; dispatch is manual/framework-integrated next."}, agent=agent))
    return {"due_count": len(jobs), "jobs": observed}


def format_jobs(jobs: list[dict]) -> str:
    rows = [{"id": j.get("id"), "state": j.get("state"), "next_run_at": j.get("next_run_at"), "name": j.get("name", "")} for j in jobs]
    return human_table(rows, ["id", "state", "next_run_at", "name"])
