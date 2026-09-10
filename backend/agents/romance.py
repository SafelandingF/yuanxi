from datetime import datetime, timedelta, timezone

from ..domain.events import event
from ..domain.ports import LanguageModel
from ..domain.romance import RomanceRequest


class RomanceAgent:
    def __init__(self, model: LanguageModel, rules: str):
        self.model = model
        self.rules = rules

    async def run(self, body: RomanceRequest):
        yield event("stage", index=0, label="正在结合出生资料分析")
        data = body.model_dump(mode="json")
        data["today"] = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        data["today_timezone"] = "Asia/Shanghai (UTC+8)"
        has_content = False
        async for text in self.model.stream(self.rules, data):
            has_content = has_content or bool(text.strip())
            yield event("delta", text=text)
        if not has_content:
            from ..domain.errors import ModelError

            raise ModelError("模型未返回分析内容，请重试")
        yield event("done")
