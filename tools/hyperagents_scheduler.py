"""hyperagents_scheduler: durable HyperAgents jobs and recurring runs.

Actions: create_job, list_jobs, get_job, update_job, cancel_job, due_jobs,
run_due_jobs, mark_job_result.
"""
import json

from helpers.tool import Tool, Response
from usr.plugins.a0_hyperagents.helpers import scheduler_service


class HyperagentsScheduler(Tool):
    async def execute(self, **kwargs) -> Response:
        action = (self.args.get("action") or "").strip()
        try:
            if action == "create_job":
                data = scheduler_service.create_job(self.args.get("job") or {}, agent=self.agent)
                msg = f"Job created id={data['id']} next_run_at={data.get('next_run_at')}."
            elif action == "list_jobs":
                jobs = scheduler_service.list_jobs(agent=self.agent, include_cancelled=bool(self.args.get("include_cancelled")))
                data = {"jobs": jobs}
                msg = scheduler_service.format_jobs(jobs)
            elif action == "get_job":
                data = {"job": scheduler_service.get_job(self.args.get("job_id", ""), agent=self.agent)}
                msg = "Job details."
            elif action == "update_job":
                data = scheduler_service.update_job(self.args.get("job_id", ""), self.args.get("updates") or {}, agent=self.agent)
                msg = f"Job {data['id']} updated."
            elif action == "cancel_job":
                data = scheduler_service.cancel_job(self.args.get("job_id", ""), agent=self.agent)
                msg = f"Job {data['id']} cancelled."
            elif action == "due_jobs":
                jobs = scheduler_service.due_jobs(agent=self.agent)
                data = {"due": jobs}
                msg = f"{len(jobs)} due jobs."
            elif action == "run_due_jobs":
                data = scheduler_service.run_due_jobs(agent=self.agent)
                msg = f"Observed {data.get('due_count', 0)} due jobs."
            elif action == "mark_job_result":
                data = scheduler_service.mark_job_result(self.args.get("job_id", ""), self.args.get("result") or {}, agent=self.agent)
                msg = f"Recorded result for {data['id']}."
            else:
                return Response(message="Unknown action. Valid: create_job, list_jobs, get_job, update_job, cancel_job, due_jobs, run_due_jobs, mark_job_result.", break_loop=False)
        except Exception as e:
            return Response(message=f"hyperagents_scheduler error: {e}", break_loop=False)
        return Response(message=f"{msg}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```", break_loop=False)
