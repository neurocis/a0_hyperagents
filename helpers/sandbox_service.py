from __future__ import annotations

import os
from pathlib import Path
from usr.plugins.a0_hyperagents.helpers.common import ensure_dir, new_id, now_iso, path_in_plugin_storage, run_cmd, write_json
from usr.plugins.a0_hyperagents.helpers.patch_service import validate_patch


def sandbox_root(agent=None) -> Path:
    return path_in_plugin_storage("sandboxes", agent=agent)


def create_sandbox(candidate_id: str = "", source_path: str = "", policy: dict | None = None, agent=None) -> dict:
    sid = candidate_id or new_id("sandbox")
    path = sandbox_root(agent) / sid
    ensure_dir(path)
    meta = {"sandbox_id": sid, "path": str(path), "source_path": source_path, "policy": policy or {}, "created_at": now_iso(), "kind": "filesystem_mvp"}
    write_json(path / "metadata.json", meta)
    return meta


def run_command(command: str, cwd: str = "", timeout: int = 120, agent=None) -> dict:
    # Conservative MVP: no shell=True, run through bash -lc only when explicitly asked by tool caller.
    return run_cmd(["bash", "-lc", command], cwd=cwd or None, timeout=timeout)


def scan_for_unsafe_paths(path: str, agent=None) -> dict:
    p = Path(path)
    findings = []
    forbidden_names = {".env", "id_rsa", "id_ed25519", "secrets"}
    if p.is_file():
        paths = [p]
    else:
        paths = [x for x in p.rglob("*") if x.is_file()] if p.exists() else []
    for x in paths:
        parts = set(x.parts)
        if forbidden_names & parts or x.name in forbidden_names:
            findings.append(str(x))
    return {"ok": not findings, "findings": findings}


def scan_for_secret_access(path: str, agent=None) -> dict:
    p = Path(path)
    findings = []
    needles = ["GITHUB_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "BEGIN PRIVATE KEY", "BEGIN OPENSSH"]
    files = [p] if p.is_file() else ([x for x in p.rglob("*") if x.is_file() and x.stat().st_size < 2_000_000] if p.exists() else [])
    for f in files:
        try:
            txt = f.read_text(errors="ignore")
        except Exception:
            continue
        for n in needles:
            if n in txt:
                findings.append({"file": str(f), "needle": n})
    return {"ok": not findings, "findings": findings}


def check_resource_limits(path: str, max_bytes: int = 250000, agent=None) -> dict:
    p = Path(path)
    size = 0
    if p.is_file():
        size = p.stat().st_size
    elif p.exists():
        size = sum(x.stat().st_size for x in p.rglob("*") if x.is_file())
    return {"ok": size <= int(max_bytes), "bytes": size, "max_bytes": int(max_bytes)}


def validate_candidate(path: str, patch_path: str = "", agent=None) -> dict:
    checks = {
        "unsafe_paths": scan_for_unsafe_paths(path, agent=agent),
        "secret_access": scan_for_secret_access(path, agent=agent),
    }
    if patch_path:
        checks["patch"] = validate_patch(patch_path, agent=agent)
    return {"ok": all(c.get("ok", False) for c in checks.values()), "checks": checks}
