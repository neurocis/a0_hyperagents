from __future__ import annotations

from pathlib import Path

from usr.plugins.a0_hyperagents.helpers.common import (
    copytree_clean, ensure_dir, git, now_iso, plugin_config, project_root,
    read_json, run_cmd, write_json,
)

PROTECTED_SNIPPETS = [
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "GITHUB_TOKEN=",
    "ANTHROPIC_API_KEY=",
    "OPENAI_API_KEY=",
]
PROTECTED_PATH_PARTS = ["/.env", "/secrets/", "/usr/secrets/", "id_rsa", "id_ed25519"]


def candidate_root(agent=None) -> Path:
    cfg = plugin_config(agent)
    return Path(cfg.get("candidate_root") or "/a0/usr/projects/a0-hyperagents/workspaces/candidate_agents")


def patch_root(agent=None) -> Path:
    cfg = plugin_config(agent)
    return Path(cfg.get("patch_root") or "/a0/usr/projects/a0-hyperagents/workspaces/patches")


def create_candidate_workspace(candidate_id: str, source_path: str = "", parent_genid: str = "", agent=None) -> dict:
    src = Path(source_path) if source_path else project_root(agent)
    dst = candidate_root(agent) / str(candidate_id)
    ensure_dir(dst.parent)
    copytree_clean(src, dst, ignore_git=True)
    # Initialize a local git repo so we can diff candidate edits cleanly.
    git(dst, "init", "-q")
    git(dst, "-c", "user.email=hyperagents@a0.local", "-c", "user.name=HyperAgents", "add", "-A")
    git(dst, "-c", "user.email=hyperagents@a0.local", "-c", "user.name=HyperAgents", "commit", "-q", "-m", "hyperagents:baseline", "--allow-empty")
    head = git(dst, "rev-parse", "HEAD").get("stdout", "").strip()
    meta = {
        "candidate_id": candidate_id,
        "source_path": str(src),
        "workspace_path": str(dst),
        "parent_genid": parent_genid,
        "baseline_commit": head,
        "created_at": now_iso(),
    }
    write_json(dst / ".hyperagents_candidate.json", meta)
    return meta


def _resolve_baseline(workspace_path: str, base_commit: str) -> str:
    if base_commit and base_commit != "HEAD":
        return base_commit
    meta = read_json(Path(workspace_path) / ".hyperagents_candidate.json", {})
    return (meta or {}).get("baseline_commit") or "HEAD"


def capture_diff(workspace_path: str, output_patch: str = "", base_commit: str = "HEAD", agent=None) -> dict:
    ws = Path(workspace_path)
    out = Path(output_patch) if output_patch else patch_root(agent) / ws.name / "model_patch.diff"
    ensure_dir(out.parent)
    base = _resolve_baseline(workspace_path, base_commit)
    if (ws / ".git").exists():
        # Stage everything so untracked files are included in diff.
        git(ws, "-c", "user.email=hyperagents@a0.local", "-c", "user.name=HyperAgents", "add", "-A")
        diff_res = git(ws, "diff", "--cached", base, timeout=120)
        diff = diff_res.get("stdout", "")
    else:
        diff_res = run_cmd(["diff", "-ruN", "--exclude=.git", "--exclude=__pycache__", str(ws.parent / ws.name), str(ws)], timeout=120)
        diff = diff_res.get("stdout", "")
    out.write_text(diff)
    size = out.stat().st_size
    return {"patch_path": str(out), "bytes": size, "empty": size == 0, "baseline_commit": base}


def validate_patch(patch_path: str, max_patch_bytes: int = 250000, agent=None) -> dict:
    p = Path(patch_path)
    findings: list[str] = []
    if not p.exists():
        return {"ok": False, "findings": ["patch file does not exist"], "bytes": 0}
    text = p.read_text(errors="replace")
    size = p.stat().st_size
    if size > int(max_patch_bytes):
        findings.append(f"patch exceeds max_patch_bytes: {size} > {max_patch_bytes}")
    for snip in PROTECTED_SNIPPETS:
        if snip in text:
            findings.append(f"possible secret material in patch: {snip}")
    for part in PROTECTED_PATH_PARTS:
        if part in text:
            findings.append(f"patch references protected path fragment: {part}")
    return {"ok": not findings, "findings": findings, "bytes": size}


def summarize_patch(patch_path: str, max_lines: int = 80) -> dict:
    p = Path(patch_path)
    if not p.exists():
        return {"summary": "Patch file missing.", "files": [], "lines": 0}
    lines = p.read_text(errors="replace").splitlines()
    files = [line[:200] for line in lines if line.startswith(("diff ", "--- ", "+++ "))]
    preview = "\n".join(lines[:max_lines])
    return {
        "summary": f"Patch has {len(lines)} lines and references {len(files)} file markers.",
        "files": files[:100],
        "lines": len(lines),
        "preview": preview,
    }


def promote_patch(patch_path: str, target_path: str = "", dry_run: bool = True, agent=None) -> dict:
    target = Path(target_path) if target_path else project_root(agent)
    validation = validate_patch(patch_path, agent=agent)
    if not validation["ok"]:
        return {"ok": False, "dry_run": dry_run, "validation": validation, "message": "Patch failed validation; not promoted."}
    if dry_run:
        check = run_cmd(["git", "-C", str(target), "apply", "--check", patch_path], timeout=120)
        return {"ok": check["ok"], "dry_run": True, "validation": validation, "check": check}
    res = run_cmd(["git", "-C", str(target), "apply", patch_path], timeout=120)
    return {"ok": res["ok"], "dry_run": False, "validation": validation, "result": res}
