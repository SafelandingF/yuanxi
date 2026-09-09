from ..agents.legacy import LegacyAnalysisAgent
from ..domain.ports import Repository
from ..domain.schemas import Profile


class LegacyAnalysisService:
    def __init__(self, repository: Repository, agent: LegacyAnalysisAgent):
        self.repository = repository
        self.agent = agent

    async def analyze(self, profile: Profile):
        result, summary = None, ""
        runner = self.agent.run(profile, self.repository.candidates())
        try:
            async for item in runner:
                if item["type"] == "result":
                    result = {k: v for k, v in item.items() if k != "type"}
                    self.repository.save(result["session_id"], result)
                elif item["type"] == "delta":
                    summary += item["text"]
                elif item["type"] == "done" and result:
                    self.repository.save(
                        result["session_id"], {**result, "summary": summary}
                    )
                yield item
        finally:
            await runner.aclose()
