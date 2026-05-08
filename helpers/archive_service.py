from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from usr.plugins.a0_hyperagents.helpers.common import (
    append_jsonl, ensure_dir, human_table, now_iso, path_in_plugin_storage,
    read_json, read_jsonl, write_json
)


def archive_path(agent=None) -> Path:
    return path_in_plugin_storage("archive.jsonl", agent=agent)


def node_dir(genid: str, agent=None) -> Path:
    return path_in_plugin_storage("nodes", str(genid), agent=agent)


def node_metadata_path(genid: str, agent=None) -> Path:
    return node_dir(genid, agent=agent) / "metadata.json"


def create_archive(project: str = "a0-hyperagents", agent=None) -> dict:
    ensure_dir(path_in_plugin_storage("nodes", agent=agent))
    ap = archive_path(agent)
    if not ap.exists():
        initial = {
            "genid": "initial",
            "parent_genid": None,
            "project": project,
            "created_at": now_iso(),
            "valid_parent": True,
            "can_select_next_parent": True,
            "scores": {},
            "summary": "Initial HyperAgents archive node.",
        }
        write_json(node_metadata_path("gen_initial", agent=agent), initial)
        append_jsonl(ap, {"current_genid": "initial", "archive": ["initial"], "created_at": now_iso()})
    return {"archive_path": str(ap), "exists": True, "entries": read_jsonl(ap)}


def latest_archive_state(agent=None) -> dict:
    rows = read_jsonl(archive_path(agent))
    if not rows:
        return {"current_genid": None, "archive": []}
    return rows[-1]


def get_node(genid: str, agent=None) -> dict | None:
    candidates = [node_metadata_path(genid, agent=agent)]
    if genid == "initial":
        candidates.append(node_metadata_path("gen_initial", agent=agent))
    if not str(genid).startswith("gen_"):
        candidates.append(node_metadata_path(f"gen_{genid}", agent=agent))
    for p in candidates:
        data = read_json(p, None)
        if isinstance(data, dict):
            return data
    return None


def add_node(node: dict, project: str = "a0-hyperagents", agent=None) -> dict:
    if not node.get("genid"):
        state = latest_archive_state(agent)
        numeric = [g for g in state.get("archive", []) if isinstance(g, int) or str(g).isdigit()]
        next_id = (max(int(g) for g in numeric) + 1) if numeric else 1
        node["genid"] = next_id
    node.setdefault("project", project)
    node.setdefault("created_at", now_iso())
    node.setdefault("valid_parent", True)
    node.setdefault("can_select_next_parent", True)
    node.setdefault("scores", {})
    node.setdefault("patch_files", [])
    genid = str(node["genid"])
    write_json(node_metadata_path(f"gen_{genid}" if not genid.startswith("gen_") and genid != "initial" else genid, agent=agent), node)

    state = latest_archive_state(agent)
    archive = list(state.get("archive", []))
    stored_id: Any = node["genid"]
    if stored_id not in archive and str(stored_id) not in [str(x) for x in archive]:
        archive.append(stored_id)
    record = {"current_genid": stored_id, "archive": archive, "updated_at": now_iso()}
    append_jsonl(archive_path(agent), record)
    return {"node": node, "archive_state": record}


def list_nodes(agent=None) -> list[dict]:
    state = latest_archive_state(agent)
    rows = []
    for genid in state.get("archive", []):
        rows.append(get_node(str(genid), agent=agent) or {"genid": genid, "missing_metadata": True})
    return rows


def update_node_metadata(genid: str, updates: dict, agent=None) -> dict:
    node = get_node(genid, agent=agent) or {"genid": genid, "created_at": now_iso()}
    node.update(updates or {})
    pgen = str(genid)
    path_id = pgen if pgen.startswith("gen_") or pgen == "initial" else f"gen_{pgen}"
    write_json(node_metadata_path(path_id, agent=agent), node)
    return node


def get_valid_parents(filters: dict | None = None, agent=None) -> list[dict]:
    filters = filters or {}
    min_safety = filters.get("min_safety_score")
    out = []
    for n in list_nodes(agent=agent):
        if n.get("valid_parent", True) is False or n.get("can_select_next_parent", True) is False:
            continue
        if min_safety is not None:
            safety = (n.get("scores") or {}).get("safety")
            if safety is not None and float(safety) < float(min_safety):
                continue
        out.append(n)
    return out


def select_parent(strategy: str = "random_valid_parent", filters: dict | None = None, agent=None) -> dict:
    parents = get_valid_parents(filters, agent=agent)
    if not parents:
        raise ValueError("No valid parents available")
    if strategy == "best_overall":
        return max(parents, key=lambda n: float((n.get("scores") or {}).get("overall", -1)))
    if strategy == "latest":
        return parents[-1]
    return random.choice(parents)


def get_lineage(genid: str, agent=None) -> list[dict]:
    lineage = []
    seen = set()
    cur = genid
    while cur and cur not in seen:
        seen.add(cur)
        node = get_node(str(cur), agent=agent)
        if not node:
            break
        lineage.append(node)
        cur = node.get("parent_genid")
    return list(reversed(lineage))


def format_nodes(nodes: list[dict]) -> str:
    rows = []
    for n in nodes:
        scores = n.get("scores") or {}
        rows.append({
            "genid": n.get("genid", ""),
            "parent": n.get("parent_genid", ""),
            "overall": scores.get("overall", ""),
            "safety": scores.get("safety", ""),
            "valid": n.get("valid_parent", True),
            "summary": str(n.get("summary", ""))[:80],
        })
    return human_table(rows, ["genid", "parent", "overall", "safety", "valid", "summary"])
