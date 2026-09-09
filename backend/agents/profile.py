from ..domain.ports import LanguageModel
from ..domain.schemas import PortraitResult


class ProfileAgent:
    def __init__(self, model: LanguageModel):
        self.model = model

    async def analyze(self, profile: dict):
        result = await self.model.structured(
            "你是关系画像助手。根据资料提炼简短关系画像及需要商量的差异，避免心理诊断和玄学。",
            profile,
            PortraitResult,
        )
        return result.model_dump()
