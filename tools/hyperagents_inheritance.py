"""hyperagents_inheritance: profile/project inheritance + generation overlays.

Actions: resolve_profile, list_mutable_artifacts, create_overlay,
validate_inheritance_graph.
"""
import json

from helpers.tool import Tool, Response
from usr.plugins.a0_hyperagents.helpers import inheritance_service


class HyperagentsInheritance(Tool):
    async def execute(self, **kwargs) -> Response:
        action = (self.args.get("action") or "").strip()
        try:
            if action == "resolve_profile":
                data = inheritance_service.resolve_profile(
                    profile=self.args.get("profile", ""),
                    project=self.args.get("project", ""),
                    generation=self.args.get("generation", ""),
                    agent=self.agent,
                )
                msg = f"Resolved profile chain for {self.args.get('profile')}."
            elif action == "list_mutable_artifacts":
                data = {"artifacts": inheritance_service.list_mutable_artifacts(self.args.get("project", ""), agent=self.agent)}
                msg = "Mutable artifact roots."
            elif action == "create_overlay":
                data = inheritance_service.create_overlay(self.args.get("generation", ""), self.args.get("files") or {}, agent=self.agent)
                msg = f"Overlay created at {data['overlay_path']}."
            elif action == "validate_inheritance_graph":
                data = inheritance_service.validate_inheritance_graph(self.args.get("project", ""), agent=self.agent)
                msg = "Inheritance graph clean." if data["ok"] else "Issues found in inheritance graph."
            else:
                return Response(message="Unknown action. Valid: resolve_profile, list_mutable_artifacts, create_overlay, validate_inheritance_graph.", break_loop=False)
        except Exception as e:
            return Response(message=f"hyperagents_inheritance error: {e}", break_loop=False)
        return Response(message=f"{msg}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```", break_loop=False)
