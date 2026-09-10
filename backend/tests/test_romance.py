import unittest
from pathlib import Path

from backend.agents.romance import RomanceAgent
from backend.domain.errors import ModelError
from backend.domain.romance import RomanceRequest

RULES = (Path(__file__).resolve().parents[1] / "agents/rules/romance.md").read_text()


class RomanceAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_rules_and_user_data_are_sent_to_model(self):
        calls = []

        class Model:
            async def stream(self, system, data):
                calls.append((system, data))
                yield "### 依据\n"
                yield "这是模型生成的分析。"

        body = RomanceRequest(
            birth_date="2000-06-15", birth_time="14:30", birth_place="杭州", year=2026
        )
        events = [e async for e in RomanceAgent(Model(), RULES).run(body)]
        self.assertEqual(calls[0][0], RULES)
        sent = calls[0][1]
        self.assertEqual(sent["today_timezone"], "Asia/Shanghai (UTC+8)")
        from datetime import datetime, timedelta, timezone

        self.assertEqual(
            sent["today"], datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        )
        self.assertEqual(
            {k: v for k, v in sent.items() if k not in ("today", "today_timezone")},
            body.model_dump(mode="json"),
        )
        self.assertEqual(events[0]["type"], "stage")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(
            "".join(e["text"] for e in events if e["type"] == "delta"),
            "### 依据\n这是模型生成的分析。",
        )

    async def test_error_is_not_replaced_by_local_fortune(self):
        class Model:
            async def stream(self, *args):
                raise ModelError("上游不可用")
                yield ""

        with self.assertRaises(ModelError):
            _ = [
                e
                async for e in RomanceAgent(Model(), RULES).run(
                    RomanceRequest(
                        birth_date="2000-06-15", birth_place="杭州", year=2026
                    )
                )
            ]

    async def test_empty_output_is_an_error(self):
        class Model:
            async def stream(self, *args):
                yield " "

        with self.assertRaises(ModelError):
            _ = [
                e
                async for e in RomanceAgent(Model(), RULES).run(
                    RomanceRequest(
                        birth_date="2000-06-15", birth_place="杭州", year=2026
                    )
                )
            ]


class BirthInputTests(unittest.TestCase):
    def test_unknown_time_and_invalid_dates(self):
        from pydantic import ValidationError

        body = RomanceRequest(birth_date="2000-06-15", birth_place="杭州", year=2026)
        self.assertIsNone(body.birth_time)
        for patch in [
            {"birth_date": "2000-02-30"},
            {"birth_date": "2100-01-01"},
            {"birth_time": "24:00"},
            {"birth_place": ""},
        ]:
            with self.assertRaises(ValidationError):
                RomanceRequest(**{**body.model_dump(), **patch})
