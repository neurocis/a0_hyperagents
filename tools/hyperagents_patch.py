"""hyperagents_patch: candidate workspace + diff utilities for HyperAgents.

Actions: create_candidate_workspace, capture_diff, validate_patch,
summarize_patch, promote_patch.
"""
import json

from helpers.tool import Tool, Response
from usr.plugins.a0_hyperagents.helpers import patch_service
from usr.plugins.a0_hyperagents.helpers.common import new_id


class HyperagentsPatch(Tool):
    async def execute(self, **kwargs) -> Response:
        action = (self.args.get("action") or "").strip()
        try:
            if action == "create_candidate_workspace":
                cid = self.args.get("candidate_id") or new_id("cand")
                data = patch_service.create_candidate_workspace(
                    candidate_id=cid,
                    source_path=self.args.get("source_path", ""),
                    parent_genid=self.args.get("parent_genid", ""),
                    agent=self.agent,
                )
                msg = f"Candidate workspace ready at {data['workspace_path']}."
            elif action == "capture_diff":
                data = patch_service.capture_diff(
                    workspace_path=self.args.get("workspace_path", ""),
                    output_patch=self.args.get("output_patch", ""),
                    base_commit=self.args.get("base_commit", "HEAD"),
                    agent=self.agent,
                )
                msg = f"Diff captured at {data['patch_path']} ({data['bytes']} bytes, empty={data['empty']})."
            elif action == "validate_patch":
                data = patch_service.validate_patch(self.args.get("patch_path", ""), max_patch_bytes=int(self.args.get("max_patch_bytes", 250000)), agent=self.agent)
                msg = "Patch OK." if data["ok"] else "Patch failed validation."
            elif action == "summarize_patch":
                data = patch_service.summarize_patch(self.args.get("patch_path", ""))
                msg = data.get("summary", "Summarized.")
            elif action == "promote_patch":
                data = patch_service.promote_patch(
                    patch_path=self.args.get("patch_path", ""),
                    target_path=self.args.get("target_path", ""),
                    dry_run=self.args.get("dry_run", True) is not False,
                    agent=self.agent,
                )
                msg = "Promotion check passed." if data["ok"] else "Promotion blocked."
            else:
                return Response(message="Unknown action. Valid: create_candidate_workspace, capture_diff, validate_patch, summarize_patch, promote_patch.", break_loop=False)
        except Exception as e:
            return Response(message=f"hyperagents_patch error: {e}", break_loop=False)
        return Response(message=f"{msg}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```", break_loop=False)
