from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLUGIN_NAME = "hyperagents"
PLUGIN_ROOT = Path("/a0/usr/plugins/a0_hyperagents")
DEFAULT_PROJECT_ROOT = Path("/a0/usr/projects/a0-hyperagents")
DEFAULT_STORAGE_ROOT = PLUGIN_ROOT / "storage"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return p


def append_jsonl(path: str | Path, data: dict) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("a") as f:
        f.write(json.dumps(data, sort_keys=True) + "\n")
    return p


def read_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def plugin_config(agent=None) -> dict:
    cfg = {}
    try:
        from helpers.plugins import get_plugin_config
        loaded = get_plugin_config(PLUGIN_NAME, agent=agent) or {}
        if isinstance(loaded, dict):
            cfg.update(loaded)
    except Exception:
        pass
    return cfg


def storage_root(agent=None) -> Path:
    cfg = plugin_config(agent)
    return Path(cfg.get("storage_root") or DEFAULT_STORAGE_ROOT)


def project_root(agent=None, explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    cfg = plugin_config(agent)
    return Path(cfg.get("project_root") or DEFAULT_PROJECT_ROOT)


def path_in_plugin_storage(*parts: str, agent=None) -> Path:
    return storage_root(agent).joinpath(*parts)


def run_cmd(argv: list[str], cwd: str | Path | None = None, timeout: int = 120, input_text: str | None = None) -> dict:
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "cmd": argv,
        }
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "returncode": 124, "stdout": e.stdout or "", "stderr": f"timeout after {timeout}s", "cmd": argv}
    except Exception as e:
        return {"ok": False, "returncode": 1, "stdout": "", "stderr": str(e), "cmd": argv}


def git(repo: str | Path, *args: str, timeout: int = 120, input_text: str | None = None) -> dict:
    return run_cmd(["git", "-C", str(repo), *args], timeout=timeout, input_text=input_text)


def new_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def copytree_clean(src: str | Path, dst: str | Path, ignore_git: bool = True) -> Path:
    srcp = Path(src)
    dstp = Path(dst)
    if dstp.exists():
        shutil.rmtree(dstp)
    ignore = shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv", "node_modules") if ignore_git else None
    shutil.copytree(srcp, dstp, ignore=ignore)
    return dstp


def human_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "No rows."
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    header = " | ".join(c.ljust(widths[c]) for c in columns)
    sep = "-+-".join("-" * widths[c] for c in columns)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns) for r in rows)
    return f"{header}\n{sep}\n{body}"
