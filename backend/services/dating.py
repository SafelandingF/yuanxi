from uuid import uuid4

from ..agents.dating import DatingAgent
from ..domain.errors import Conflict, InvalidInput, NotFound
from ..domain.ports import Repository
from ..domain.schemas import DateRequest


class DatingService:
    def __init__(self, repository: Repository, agent: DatingAgent):
        self.repository = repository
        self.agent = agent

    def plan(self, body: DateRequest):
        session = self.repository.get(body.session_id)
        if not session or "candidates" not in session:
            raise NotFound("画像已失效，请重新分析")
        candidate = next(
            (c for c in session["candidates"] if c["id"] == body.candidate_id), None
        )
        if (
            session.get("kind") == "agent"
            and session.get("selected_id") != body.candidate_id
        ):
            raise Conflict("请先在匹配助手中确认这位候选")
        if not candidate:
            raise InvalidInput("请选择当前分析中的候选")
        return self._run(session, candidate, body)

    async def _run(self, session, candidate, body):
        result, summary = None, ""
        runner = self.agent.run(session, candidate, body)
        try:
            async for item in runner:
                if item["type"] == "result":
                    result = {k: v for k, v in item.items() if k != "type"}
                elif item["type"] == "delta":
                    summary += item["text"]
                elif item["type"] == "done" and result is not None:
                    self.repository.save(
                        "date-" + str(uuid4()),
                        {
                            "session_id": body.session_id,
                            "candidate_id": body.candidate_id,
                            **result,
                            "summary": summary,
                        },
                    )
                    latest = self.repository.get(body.session_id)
                    if (
                        session.get("kind") == "agent"
                        and latest
                        and latest.get("revision") == session.get("revision")
                        and latest.get("selected_id") == body.candidate_id
                    ):
                        latest["latest_date"] = {
                            "request": body.model_dump(),
                            "result": result,
                            "summary": summary,
                        }
                        self.repository.save(body.session_id, latest)
                yield item
        finally:
            await runner.aclose()
