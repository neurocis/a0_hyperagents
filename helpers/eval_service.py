from __future__ import annotations

from pathlib import Path
from usr.plugins.a0_hyperagents.helpers.common import append_jsonl, now_iso, path_in_plugin_storage, run_cmd, write_json
from usr.plugins.a0_hyperagents.helpers.sandbox_service import validate_candidate

DOMAINS = [
    "agent_zero_tool_use",
    "agent_zero_scheduler_reliability",
    "agent_zero_superordinate_coordination",
    "agent_zero_memory_grounding",
    "agent_zero_project_patch_quality",
    "agent_zero_safety_compliance",
]


def evals_path(agent=None) -> Path:
    return path_in_plugin_storage("evals.jsonl", agent=agent)


def list_eval_domains() -> list[str]:
    return DOMAINS


def score_candidate(candidate_id: str, workspace_path: str = "", patch_path: str = "", domains: list[str] | None = None, agent=None) -> dict:
    domains = domains or DOMAINS
    checks = validate_candidate(workspace_path, patch_path=patch_path, agent=agent) if workspace_path else {"ok": True, "checks": {}}
    scores = {}
    # MVP heuristic scores: safety gates plus optional syntax/import checks for python files.
    safety = 1.0 if checks.get("ok") else 0.0
    scores["agent_zero_safety_compliance"] = safety
    if workspace_path and Path(workspace_path).exists():
        py_files = [str(p) for p in Path(workspace_path).rglob("*.py") if "__pycache__" not in str(p)]
        compile_ok = True
        if py_files:
            res = run_cmd(["python3", "-m", "py_compile", *py_files[:200]], timeout=120)
            compile_ok = res["ok"]
        scores["agent_zero_project_patch_quality"] = 1.0 if compile_ok else 0.0
    for d in domains:
        scores.setdefault(d, safety)
    overall = sum(scores[d] for d in scores) / max(len(scores), 1)
    return {"candidate_id": candidate_id, "domains": domains, "scores": scores, "overall": overall, "checks": checks, "created_at": now_iso()}


def write_eval_report(report: dict, candidate_id: str = "", agent=None) -> dict:
    cid = candidate_id or report.get("candidate_id") or "unknown"
    path = path_in_plugin_storage("nodes", f"gen_{cid}" if not str(cid).startswith("gen_") else str(cid), "eval_report.json", agent=agent)
    write_json(path, report)
    append_jsonl(evals_path(agent), report)
    return {"report_path": str(path), "report": report}


def run_eval_suite(candidate_id: str, workspace_path: str = "", patch_path: str = "", domains: list[str] | None = None, agent=None) -> dict:
    report = score_candidate(candidate_id, workspace_path, patch_path, domains, agent=agent)
    return write_eval_report(report, candidate_id=candidate_id, agent=agent)


def compare_candidates(a: dict, b: dict) -> dict:
    return {"a_overall": a.get("overall"), "b_overall": b.get("overall"), "winner": "a" if float(a.get("overall", 0)) >= float(b.get("overall", 0)) else "b"}
