"""hyperagents_eval: evaluation harness for HyperAgents candidates.

Actions: list_eval_domains, run_eval_suite, score_candidate,
write_eval_report, compare_candidates.
"""
import json

from helpers.tool import Tool, Response
from usr.plugins.a0_hyperagents.helpers import eval_service


class HyperagentsEval(Tool):
    async def execute(self, **kwargs) -> Response:
        action = (self.args.get("action") or "").strip()
        try:
            if action == "list_eval_domains":
                data = {"domains": eval_service.list_eval_domains()}
                msg = "Available eval domains."
            elif action == "score_candidate":
                data = eval_service.score_candidate(
                    candidate_id=self.args.get("candidate_id", ""),
                    workspace_path=self.args.get("workspace_path", ""),
                    patch_path=self.args.get("patch_path", ""),
                    domains=self.args.get("domains"),
                    agent=self.agent,
                )
                msg = f"Scored candidate overall={data.get('overall')}."
            elif action == "run_eval_suite":
                data = eval_service.run_eval_suite(
                    candidate_id=self.args.get("candidate_id", ""),
                    workspace_path=self.args.get("workspace_path", ""),
                    patch_path=self.args.get("patch_path", ""),
                    domains=self.args.get("domains"),
                    agent=self.agent,
                )
                msg = f"Eval report saved at {data.get('report_path')}."
            elif action == "write_eval_report":
                data = eval_service.write_eval_report(self.args.get("report") or {}, candidate_id=self.args.get("candidate_id", ""), agent=self.agent)
                msg = f"Report written at {data.get('report_path')}."
            elif action == "compare_candidates":
                data = eval_service.compare_candidates(self.args.get("a") or {}, self.args.get("b") or {})
                msg = f"Winner: {data.get('winner')}."
            else:
                return Response(message="Unknown action. Valid: list_eval_domains, run_eval_suite, score_candidate, write_eval_report, compare_candidates.", break_loop=False)
        except Exception as e:
            return Response(message=f"hyperagents_eval error: {e}", break_loop=False)
        return Response(message=f"{msg}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```", break_loop=False)
