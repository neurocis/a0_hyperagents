# HyperAgents Plugin for Agent Zero

Unified project-aware HyperAgents-style plugin exposing six tools:

- `hyperagents_archive`
- `hyperagents_patch`
- `hyperagents_eval`
- `hyperagents_scheduler`
- `hyperagents_sandbox`
- `hyperagents_inheritance`

The plugin is intentionally one artifact named `a0_hyperagents`, with modular internal services for archive, patching, evaluation, scheduling, sandboxing, and inheritance.

This MVP is conservative: it creates candidate workspaces, captures patches, records archive metadata, runs lightweight eval/safety checks, and schedules jobs. Promotion is dry-run/manual by default.

## Dependencies

### Hard dependencies

None. The `a0_hyperagents` plugin runs entirely on its own modules under `usr.plugins.a0_hyperagents.*` and standard Agent Zero framework helpers (`helpers.tool`, `helpers.plugins`). It does not import from any other user plugin.

Required by Agent Zero core (already shipped with the framework):

- `helpers.tool` (provides the `Tool` / `Response` base classes used by every `hyperagents_*` tool)
- `helpers.plugins` (used to read this plugin's settings via `get_plugin_config`)
- A working `git` binary on `PATH` (used by `hyperagents_patch` to baseline candidate workspaces and capture diffs)
- A working Python 3 interpreter on `PATH` (used by `hyperagents_eval` for `python3 -m py_compile` smoke checks)

### Recommended companion plugins

These are **not required** for the plugin to load or for any of the six tools to function, but they are strongly recommended for the full HyperAgents-style workflow described in [Section 9 of "How to use this plugin"](#9-recommended-workflow-with-superordinates).

| Plugin | Why you want it | What `a0_hyperagents` does without it |
|---|---|---|
| [`a0_superordinates`](../a0_superordinates/) | Spawns and coordinates the persistent `HyperManager`, `HyperMetaAgent`, `HyperEvaluator`, `HyperArchivist`, `HyperSafetyReviewer`, and `HyperScheduler` superordinates that drive the HyperLoop end-to-end. Also provides cross-context messaging used to delegate candidate edits and eval runs. | All six `hyperagents_*` tools still work; the loop must be driven manually by the calling agent or by hand. |
| [`a0_scheduler`](../a0_scheduler/) | Provides the framework-level cron/timer engine that can fire scheduled jobs into agent contexts on a real clock, including across restarts. | `hyperagents_scheduler` still persists durable jobs in `storage/jobs.jsonl` and supports `create_job`, `list_jobs`, `due_jobs`, `mark_job_result`, etc. The MVP `run_due_jobs` only **observes** due jobs and rolls forward `next_run_at`; without `a0_scheduler` (or another external trigger), nothing automatically dispatches the job to a target agent. |

### Optional companion plugins

| Plugin | Use case |
|---|---|
| [`a0_cognee`](../a0_cognee/) or [`a0_hindsight`](../a0_hindsight/) | Long-term memory grounding for `hyper_researcher` / `hyper_archivist` profiles when summarizing the repo and paper into project knowledge. |
| `_code_execution` (core) | Used by candidate authoring agents (and by humans during manual review) to edit and test candidate workspaces under `workspaces/candidate_agents/`. Always available because it is a core plugin. |
| `_text_editor` (core) | Same as above: used to read/write/patch candidate files. Always available because it is a core plugin. |

### External / system dependencies

- `git >= 2.0` (Debian/Kali default works)
- Python 3.10+ standard library only; no third-party Python packages are required by this plugin
- Filesystem write access to:
  - `/a0/usr/plugins/a0_hyperagents/storage/`
  - `/a0/usr/projects/a0-hyperagents/workspaces/candidate_agents/`
  - `/a0/usr/projects/a0-hyperagents/workspaces/patches/`

### Project dependency

The plugin is shipped with project-scoped defaults pointing at the **`a0-hyperagents` Agent Zero project** at `/a0/usr/projects/a0-hyperagents/`. You can repoint `project_root`, `candidate_root`, and `patch_root` in `default_config.yaml` (or via the Settings modal) to use this plugin against a different Agent Zero project; no other plugin code changes are needed.

## How to use this plugin

This section is the practical entry point. Follow the steps in order the first time you use the plugin.

### 1. Enable the plugin

1. Open the Agent Zero **Plugin List** UI.
2. Locate `a0_hyperagents` and toggle it ON for the desired scope (global, project, or agent profile).
3. Optional: open the plugin **Settings** modal and review the values from `default_config.yaml` (project ID, sandbox/promotion safety toggles, max patch size, storage paths). Adjust per project or per profile as needed.

After enable, the six `hyperagents_*` tools become available to any agent in the active scope.

### 2. Initialize storage (once per install)

From the Plugin List UI use **Initialize / Run Script** to invoke `execute.py`, or run from a shell:

```bash
python3 /a0/usr/plugins/a0_hyperagents/execute.py
```

This ensures `storage/`, `storage/nodes/gen_initial/`, and `storage/sandboxes/` exist.

### 3. Create the archive

The archive is the persistent record of every candidate generation, its scores, lineage, and patch files.

```json
{
  "tool_name": "hyperagents_archive",
  "tool_args": { "action": "create_archive" }
}
```

This writes `storage/archive.jsonl` and the `gen_initial` node.

### 4. Run one HyperLoop generation manually

A single HyperLoop generation has five phases. The tool calls below are the canonical sequence.

#### 4a. Select a parent

```json
{
  "tool_name": "hyperagents_archive",
  "tool_args": {
    "action": "select_parent",
    "strategy": "random_valid_parent"
  }
}
```

Supported strategies: `random_valid_parent` (default), `latest`, `best_overall`.

#### 4b. Materialize a candidate workspace

```json
{
  "tool_name": "hyperagents_patch",
  "tool_args": {
    "action": "create_candidate_workspace",
    "candidate_id": "cand_demo_001",
    "parent_genid": "initial"
  }
}
```

This copies the project root into `workspaces/candidate_agents/cand_demo_001/`, initializes a local git repo, and records a baseline commit. Edit the candidate workspace there (manually, via a subordinate developer agent, or via the meta agent).

#### 4c. Capture and validate the diff

```json
{
  "tool_name": "hyperagents_patch",
  "tool_args": {
    "action": "capture_diff",
    "workspace_path": "/a0/usr/projects/a0-hyperagents/workspaces/candidate_agents/cand_demo_001"
  }
}
```

```json
{
  "tool_name": "hyperagents_patch",
  "tool_args": {
    "action": "validate_patch",
    "patch_path": "/a0/usr/projects/a0-hyperagents/workspaces/patches/cand_demo_001/model_patch.diff"
  }
}
```

Validation rejects oversized patches and patches that contain protected paths or secret-like content.

#### 4d. Add the candidate to the archive

```json
{
  "tool_name": "hyperagents_archive",
  "tool_args": {
    "action": "add_node",
    "payload": {
      "parent_genid": "initial",
      "summary": "Demo candidate that improves <something>",
      "patch_files": [
        "/a0/usr/projects/a0-hyperagents/workspaces/patches/cand_demo_001/model_patch.diff"
      ]
    }
  }
}
```

This returns the new `genid`. Use it for the eval step.

#### 4e. Evaluate the candidate

```json
{
  "tool_name": "hyperagents_eval",
  "tool_args": {
    "action": "run_eval_suite",
    "candidate_id": "1",
    "workspace_path": "/a0/usr/projects/a0-hyperagents/workspaces/candidate_agents/cand_demo_001",
    "patch_path": "/a0/usr/projects/a0-hyperagents/workspaces/patches/cand_demo_001/model_patch.diff"
  }
}
```

The eval report is written to `storage/nodes/gen_<id>/eval_report.json` and appended to `storage/evals.jsonl`. Update the archive node with the resulting scores:

```json
{
  "tool_name": "hyperagents_archive",
  "tool_args": {
    "action": "update_node_metadata",
    "genid": "1",
    "payload": {
      "updates": {
        "scores": {
          "overall": 1.0,
          "safety": 1.0
        }
      }
    }
  }
}
```

### 5. Schedule recurring HyperLoop work

Durable jobs persist across restarts in `storage/jobs.jsonl`.

```json
{
  "tool_name": "hyperagents_scheduler",
  "tool_args": {
    "action": "create_job",
    "job": {
      "name": "nightly hyperloop",
      "schedule": { "type": "interval", "every_seconds": 86400 },
      "task": { "message": "Run one safe HyperLoop generation, evaluate it, and archive the result." }
    }
  }
}
```

List, observe, and complete jobs:

```json
{ "tool_name": "hyperagents_scheduler", "tool_args": { "action": "list_jobs" } }
```

```json
{ "tool_name": "hyperagents_scheduler", "tool_args": { "action": "run_due_jobs" } }
```

Note: the MVP `run_due_jobs` observes due jobs and rolls forward `next_run_at`. Wiring it to actually launch a target superordinate is the next integration step.

### 6. Run safety and sandbox checks

Always validate a candidate before any promotion:

```json
{
  "tool_name": "hyperagents_sandbox",
  "tool_args": {
    "action": "validate_candidate",
    "path": "/a0/usr/projects/a0-hyperagents/workspaces/candidate_agents/cand_demo_001",
    "patch_path": "/a0/usr/projects/a0-hyperagents/workspaces/patches/cand_demo_001/model_patch.diff"
  }
}
```

This runs `scan_for_unsafe_paths`, `scan_for_secret_access`, and patch validation in one call.

### 7. Inspect inheritance and overlays

```json
{
  "tool_name": "hyperagents_inheritance",
  "tool_args": {
    "action": "resolve_profile",
    "profile": "hyper_meta_agent"
  }
}
```

```json
{
  "tool_name": "hyperagents_inheritance",
  "tool_args": { "action": "list_mutable_artifacts" }
}
```

Use `create_overlay` to attach generation-specific prompt or policy overrides under `storage/nodes/gen_<id>/overlay/`.

### 8. Promote a winning candidate (manual gate)

Promotion is **dry-run by default** and **requires human approval** in the default configuration.

Dry-run check:

```json
{
  "tool_name": "hyperagents_patch",
  "tool_args": {
    "action": "promote_patch",
    "patch_path": "/a0/usr/projects/a0-hyperagents/workspaces/patches/cand_demo_001/model_patch.diff",
    "dry_run": true
  }
}
```

Apply the patch (only after explicit human approval and only if `require_human_promotion` is intentionally relaxed):

```json
{
  "tool_name": "hyperagents_patch",
  "tool_args": {
    "action": "promote_patch",
    "patch_path": "/a0/usr/projects/a0-hyperagents/workspaces/patches/cand_demo_001/model_patch.diff",
    "target_path": "/a0/usr/projects/a0-hyperagents",
    "dry_run": false
  }
}
```

### 9. Recommended workflow with superordinates

For real autonomous use, drive the loop through a persistent superordinate tree:

- `HyperManager` owns the run, delegates, and maintains state.
- `HyperMetaAgent` performs candidate self-modification inside the candidate workspace only.
- `HyperEvaluator` runs `hyperagents_eval`.
- `HyperArchivist` updates archive nodes and lineage.
- `HyperSafetyReviewer` gates promotion via `hyperagents_sandbox.validate_candidate`.
- `HyperScheduler` creates and observes recurring jobs.

Spawn them with the `a0_superordinates` plugin and have each one use only the `hyperagents_*` actions matching its role.

### 10. Where things live

| Artifact | Path |
|---|---|
| Plugin code | `/a0/usr/plugins/a0_hyperagents/` |
| Archive log | `/a0/usr/plugins/a0_hyperagents/storage/archive.jsonl` |
| Per-generation metadata + reports | `/a0/usr/plugins/a0_hyperagents/storage/nodes/gen_<id>/` |
| Job log | `/a0/usr/plugins/a0_hyperagents/storage/jobs.jsonl` |
| Eval log | `/a0/usr/plugins/a0_hyperagents/storage/evals.jsonl` |
| Candidate workspaces | `/a0/usr/projects/a0-hyperagents/workspaces/candidate_agents/` |
| Patch outputs | `/a0/usr/projects/a0-hyperagents/workspaces/patches/` |
| Plugin agent profiles | `/a0/usr/plugins/a0_hyperagents/agents/` |

### 11. Safety defaults

- `require_sandbox: true`
- `require_human_promotion: true`
- `allow_network_in_sandbox: false`
- `max_patch_bytes: 250000`
- `promote_patch` defaults to `dry_run: true`

Do not relax these without an explicit project decision and a documented rollback plan.
