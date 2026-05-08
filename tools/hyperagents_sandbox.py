"""hyperagents_sandbox: lightweight safety checks and isolated workspaces.

Actions: create_sandbox, run_command, scan_for_unsafe_paths,
scan_for_secret_access, check_resource_limits, validate_candidate.
"""
import json

from helpers.tool import Tool, Response
from usr.plugins.a0_hyperagents.helpers import sandbox_service


class HyperagentsSandbox(Tool):
    async def execute(self, **kwargs) -> Response:
        action = (self.args.get("action") or "").strip()
        try:
            if action == "create_sandbox":
                data = sandbox_service.create_sandbox(
                    candidate_id=self.args.get("candidate_id", ""),
                    source_path=self.args.get("source_path", ""),
                    policy=self.args.get("policy"),
                    agent=self.agent,
                )
                msg = f"Sandbox created at {data['path']}."
            elif action == "run_command":
                data = sandbox_service.run_command(
                    command=self.args.get("command", ""),
                    cwd=self.args.get("cwd", ""),
                    timeout=int(self.args.get("timeout", 120)),
                    agent=self.agent,
                )
                msg = f"Command exited {data.get('returncode')}."
            elif action == "scan_for_unsafe_paths":
                data = sandbox_service.scan_for_unsafe_paths(self.args.get("path", ""), agent=self.agent)
                msg = "Path scan ok." if data["ok"] else "Unsafe path findings detected."
            elif action == "scan_for_secret_access":
                data = sandbox_service.scan_for_secret_access(self.args.get("path", ""), agent=self.agent)
                msg = "No secret-like content found." if data["ok"] else "Possible secret material detected."
            elif action == "check_resource_limits":
                data = sandbox_service.check_resource_limits(self.args.get("path", ""), max_bytes=int(self.args.get("max_bytes", 250000)), agent=self.agent)
                msg = "Within size limits." if data["ok"] else "Size limit exceeded."
            elif action == "validate_candidate":
                data = sandbox_service.validate_candidate(self.args.get("path", ""), patch_path=self.args.get("patch_path", ""), agent=self.agent)
                msg = "Candidate passes safety checks." if data["ok"] else "Candidate failed safety checks."
            else:
                return Response(message="Unknown action. Valid: create_sandbox, run_command, scan_for_unsafe_paths, scan_for_secret_access, check_resource_limits, validate_candidate.", break_loop=False)
        except Exception as e:
            return Response(message=f"hyperagents_sandbox error: {e}", break_loop=False)
        return Response(message=f"{msg}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```", break_loop=False)
