import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from backend.core.config import ModelConfig, Settings
from backend.domain.schemas import DateChoice, MatchResult, PortraitResult
from backend.infrastructure.ark import Ark
from backend.infrastructure.sqlite import Store
from backend.main import create_app

PROFILE = {
    "name": "测试用户",
    "age": 23,
    "city": "杭州",
    "goal": "认真长久",
    "rhythm": "规律慢生活",
    "interests": ["咖啡", "电影", "散步"],
    "companionship": "每周 2–3 次",
    "note": "想有共同的周末",
}


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "test.db")
        with self.store.connect() as db:
            db.execute("DELETE FROM candidates WHERE id > 120")
        self.settings = Settings(
            database_path=Path(self.temp.name) / "test.db",
            llm=ModelConfig(api_key="test-only"),
        )
        self.model = Ark(self.settings.llm)
        self.app = create_app(self.settings, self.store, self.model)
        self.roles = []

        async def structured(system, data, schema, validate=None):
            self.roles.append(schema.__name__)
            if schema == PortraitResult:
                r = schema(
                    relationship_type="稳定型",
                    summary="重视陪伴",
                    core_preferences=["共同兴趣"],
                    possible_conflicts=[],
                )
            elif schema == MatchResult:
                r = schema(
                    candidates=[
                        {
                            "id": c["id"],
                            "strengths": ["共同兴趣"],
                            "conflicts": ["频率需沟通"],
                            "explanation": "基于实际资料",
                        }
                        for c in data["candidates"]
                    ]
                )
            elif schema == DateChoice:
                r = schema(
                    meal_id="simple",
                    activity_id="book",
                    drink_id="tea",
                    reason="在预算内安排轻松活动",
                    conflict_detected=True,
                    conflict_description="见面频率差异",
                )
            else:
                r = schema(explanation="双方见面频率有差异，可以提前沟通。")
            if validate:
                validate(r)
            return r

        async def stream(*args):
            yield "### 分析\n"
            yield "这是基于已校验数据的说明。"

        self.json_patch = patch.object(self.model, "structured", structured)
        self.stream_patch = patch.object(self.model, "stream", stream)
        self.json_patch.start()
        self.stream_patch.start()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.model.aclose()
        self.json_patch.stop()
        self.stream_patch.stop()
        self.temp.cleanup()

    def events(self, response):
        return [
            json.loads(line[5:])
            for line in response.text.splitlines()
            if line.startswith("data:")
        ]

    async def analysis(self):
        response = await self.client.post("/api/analyze", json=PROFILE)
        self.assertEqual(response.status_code, 200)
        events = self.events(response)
        self.assertEqual(events[-1]["type"], "done")
        return next(e for e in events if e["type"] == "result")

    async def test_full_feedback_and_budget(self):
        result = await self.analysis()
        self.assertEqual(result["sample_count"], 120)
        self.assertEqual(sum(result["distribution"].values()), 120)
        candidate = next(
            c for c in result["candidates"] if c["companionship"] == "每月 1–2 次"
        )
        payload = {
            "session_id": result["session_id"],
            "candidate_id": candidate["id"],
            "budget": 30,
            "start": "20:00",
        }
        for _ in range(2):
            events = self.events(await self.client.post("/api/date/plan", json=payload))
            self.assertEqual(events[-1]["type"], "done")
            date = next(e for e in events if e["type"] == "result")
            self.assertTrue(date["feedback"])
            self.assertEqual(date["final_score"], candidate["score"] - 10)
            self.assertLessEqual(sum(p["cost"] for p in date["plan"]), 30)
            self.assertEqual(
                [p["time"] for p in date["plan"]], ["20:00", "21:15", "22:05"]
            )
        self.assertIn("FeedbackResult", self.roles)

    async def test_unknown_candidate_rejected(self):
        result = await self.analysis()
        response = await self.client.post(
            "/api/date/plan",
            json={
                "session_id": result["session_id"],
                "candidate_id": 999,
                "budget": 100,
                "start": "18:00",
            },
        )
        self.assertEqual(response.status_code, 422)

    async def test_invalid_inputs(self):
        for bad in (
            {**PROFILE, "age": 17},
            {**PROFILE, "interests": []},
            {**PROFILE, "name": ""},
        ):
            self.assertEqual(
                (await self.client.post("/api/analyze", json=bad)).status_code, 422
            )
        for start in ("20:01", "25:00", "19:99"):
            self.assertEqual(
                (
                    await self.client.post(
                        "/api/date/plan",
                        json={
                            "session_id": "x",
                            "candidate_id": 1,
                            "budget": 30,
                            "start": start,
                        },
                    )
                ).status_code,
                422,
            )

    async def test_upstream_failure_is_explicit(self):
        from backend.domain.errors import ModelError

        async def fail(*args):
            raise ModelError("方舟请求超时，请重试")

        with patch.object(self.model, "structured", fail):
            events = self.events(await self.client.post("/api/analyze", json=PROFILE))
        self.assertEqual(events[-1]["type"], "error")
        self.assertFalse(any(e["type"] == "done" for e in events))

    async def test_health_does_not_expose_key(self):
        response = await self.client.get("/api/health")
        self.assertNotIn(self.settings.llm.api_key.get_secret_value(), response.text)

    async def test_no_conflict_no_adjustment(self):
        result = await self.analysis()
        candidate = next(
            c for c in result["candidates"] if c["companionship"] == "每周 1 次"
        )
        events = self.events(
            await self.client.post(
                "/api/date/plan",
                json={
                    "session_id": result["session_id"],
                    "candidate_id": candidate["id"],
                    "budget": 120,
                    "start": "18:00",
                },
            )
        )
        date = next(e for e in events if e["type"] == "result")
        self.assertFalse(date["feedback"])
        self.assertEqual(date["initial_score"], date["final_score"])


if __name__ == "__main__":
    unittest.main()
