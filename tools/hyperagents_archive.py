"""hyperagents_archive: archive of HyperAgents-style candidate generations.

Actions: create_archive, add_node, get_node, list_nodes, get_valid_parents,
select_parent, update_node_metadata, get_lineage.
"""
import json

from helpers.tool import Tool, Response
from usr.plugins.a0_hyperagents.helpers import archive_service


class HyperagentsArchive(Tool):
    async def execute(self, **kwargs) -> Response:
        action = (self.args.get("action") or kwargs.get("action") or "").strip()
        project = self.args.get("project") or "a0-hyperagents"
        payload = self.args.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        try:
            if action == "create_archive":
                data = archive_service.create_archive(project=project, agent=self.agent)
                msg = f"Archive ready at {data['archive_path']}."
            elif action == "add_node":
                node = payload or {k: v for k, v in self.args.items() if k not in {"action", "project", "payload"}}
                data = archive_service.add_node(node, project=project, agent=self.agent)
                msg = f"Added archive node genid={data['node']['genid']}."
            elif action == "get_node":
                genid = payload.get("genid") or self.args.get("genid")
                data = archive_service.get_node(str(genid), agent=self.agent)
                msg = "Node found." if data else f"No node with genid={genid}."
            elif action == "list_nodes":
                nodes = archive_service.list_nodes(agent=self.agent)
                data = {"nodes": nodes}
                msg = archive_service.format_nodes(nodes)
            elif action == "get_valid_parents":
                filters = payload.get("filters") if isinstance(payload, dict) else None
                nodes = archive_service.get_valid_parents(filters, agent=self.agent)
                data = {"parents": nodes}
                msg = archive_service.format_nodes(nodes)
            elif action == "select_parent":
                strategy = payload.get("strategy") or self.args.get("strategy") or "random_valid_parent"
                node = archive_service.select_parent(strategy=strategy, filters=payload.get("filters"), agent=self.agent)
                data = {"parent": node, "strategy": strategy}
                msg = f"Selected parent genid={node.get('genid')} via {strategy}."
            elif action == "update_node_metadata":
                genid = payload.get("genid") or self.args.get("genid")
                updates = payload.get("updates") or payload
                data = archive_service.update_node_metadata(str(genid), updates, agent=self.agent)
                msg = f"Updated metadata for genid={genid}."
            elif action == "get_lineage":
                genid = payload.get("genid") or self.args.get("genid")
                data = {"lineage": archive_service.get_lineage(str(genid), agent=self.agent)}
                msg = f"Lineage retrieved for genid={genid}."
            else:
                return Response(message=f"Unknown action '{action}'. Valid: create_archive, add_node, get_node, list_nodes, get_valid_parents, select_parent, update_node_metadata, get_lineage.", break_loop=False)
        except Exception as e:
            return Response(message=f"hyperagents_archive error: {e}", break_loop=False)

        message = f"{msg}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```"
        return Response(message=message, break_loop=False)
