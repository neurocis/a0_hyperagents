from __future__ import annotations

from pathlib import Path
from usr.plugins.a0_hyperagents.helpers.common import project_root, write_json


def profile_roots(project: str = "", agent=None) -> list[Path]:
    roots = []
    pr = project_root(agent, project) if project else project_root(agent)
    roots.append(pr / ".a0proj" / "agents")
    roots.append(Path("/a0/usr/agents"))
    roots.append(Path("/a0/usr/plugins/a0_hyperagents/agents"))
    return roots


def find_profile(profile: str, project: str = "", agent=None) -> Path | None:
    for r in profile_roots(project, agent=agent):
        p = r / profile
        if p.exists():
            return p
    return None


def resolve_profile(profile: str, project: str = "", generation: str = "", agent=None) -> dict:
    chain = []
    seen = set()
    cur = profile
    while cur and cur not in seen:
        seen.add(cur)
        p = find_profile(cur, project, agent=agent)
        meta = {"profile": cur, "path": str(p) if p else "", "exists": bool(p)}
        parent = ""
        if p and (p / "agent.yaml").exists():
            txt = (p / "agent.yaml").read_text(errors="ignore")
            meta["agent_yaml"] = txt
            for line in txt.splitlines():
                if line.strip().startswith("extends:"):
                    parent = line.split(":", 1)[1].strip().strip('"\'')
                    break
        chain.append(meta)
        cur = parent
    return {"profile": profile, "generation": generation, "chain": list(reversed(chain))}


def list_mutable_artifacts(project: str = "", agent=None) -> list[str]:
    pr = project_root(agent, project) if project else project_root(agent)
    candidates = [pr / ".a0proj" / "instructions", pr / ".a0proj" / "agents", Path("/a0/usr/plugins/a0_hyperagents/prompts"), Path("/a0/usr/plugins/a0_hyperagents/default_config.yaml")]
    return [str(p) for p in candidates if p.exists()]


def create_overlay(generation: str, files: dict, agent=None) -> dict:
    base = Path("/a0/usr/plugins/a0_hyperagents/storage/nodes") / (generation if generation.startswith("gen_") else f"gen_{generation}") / "overlay"
    written = []
    for rel, content in (files or {}).items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(content))
        written.append(str(p))
    return {"generation": generation, "overlay_path": str(base), "files": written}


def validate_inheritance_graph(project: str = "", agent=None) -> dict:
    issues = []
    for root in profile_roots(project, agent=agent):
        if not root.exists():
            continue
        for p in root.iterdir():
            if not p.is_dir():
                continue
            res = resolve_profile(p.name, project, agent=agent)
            names = [x["profile"] for x in res["chain"]]
            if len(names) != len(set(names)):
                issues.append({"profile": p.name, "issue": "cycle"})
    return {"ok": not issues, "issues": issues}
