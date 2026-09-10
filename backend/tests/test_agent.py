import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
from test_app import PROFILE

from backend.core.config import ModelConfig, Settings
from backend.domain.errors import ModelError
from backend.domain.schemas import PortraitResult
from backend.infrastructure.ark import Ark
from backend.infrastructure.sqlite import Store
from backend.main import create_app


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "test.db")
        self.settings = Settings(
            database_path=Path(self.temp.name) / "test.db",
            llm=ModelConfig(api_key="test-only"),
        )
        self.model = Ark(self.settings.llm)
        self.app = create_app(self.settings, self.store, self.model)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )
        self.sid = (await self.client.post("/api/agent/sessions", json=PROFILE)).json()[
            "session_id"
        ]
        self.queue = []
        self.received = []

        async def agent_step(messages, tools):
            self.received.append(messages.copy())
            item = self.queue.pop(0)
            if isinstance(item, Exception):
                raise item
            if callable(item):
                await item()
            elif isinstance(item, list):
                yield {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": str(uuid4()),
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": json.dumps(args),
                                },
                            }
                            for name, args in item
                        ],
                    },
                }
            else:
                yield {"type": "delta", "text": item}
                yield {
                    "type": "message",
                    "message": {"role": "assistant", "content": item},
                }

        async def structured(*args):
            return PortraitResult(
                relationship_type="稳定型",
                summary="重视陪伴",
                core_preferences=["共同兴趣"],
                possible_conflicts=[],
            )

        self.agent_patch = patch.object(self.model, "agent_step", agent_step)
        self.structured_patch = patch.object(self.model, "structured", structured)
        self.agent_patch.start()
        self.structured_patch.start()

    async def asyncTearDown(self):
        await self.client.aclose()
        self.agent_patch.stop()
        self.structured_patch.stop()
        await self.model.aclose()
        self.temp.cleanup()

    def events(self, r):
        return [
            json.loads(line[5:])
            for line in r.text.splitlines()
            if line.startswith("data:")
        ]

    async def send(self, text="推荐一下", selection=None, request_id=None):
        body = {"request_id": request_id or str(uuid4()), "text": text}
        if selection:
            body["selection"] = selection
        return await self.client.post(f"/api/agent/sessions/{self.sid}/chat", json=body)

    async def recommend(self):
        self.queue.extend(
            [[("analyze_profile", {})], [("search_candidates", {})], "看看这些共同点。"]
        )
        events = self.events(await self.send())
        self.assertEqual(events[-1]["type"], "done")
        return next(e["session"] for e in events if e["type"] == "state")

    async def test_native_tool_loop_cards_persistence_and_idempotency(self):
        session = await self.recommend()
        self.assertEqual(len(session["candidates"]), 3)
        self.assertIsNone(session["selected_id"])
        self.assertNotIn("history", session)
        self.assertTrue(any(m["role"] == "tool" for m in self.received[-1]))
        cards = [
            p["card"]["component"]
            for p in session["turns"][0]["parts"]
            if p["type"] == "card"
        ]
        self.assertEqual(cards, ["profile", "candidates"])
        selection = {
            "candidate_id": session["candidates"][0]["id"],
            "revision": session["revision"],
        }
        rid = str(uuid4())
        result = self.events(await self.send("我选这位", selection, rid))
        saved = next(e["session"] for e in result if e["type"] == "state")
        self.assertEqual(saved["selected_id"], selection["candidate_id"])
        replay = self.events(await self.send("我选这位", selection, rid))
        self.assertEqual(len(replay[0]["session"]["turns"]), 2)
        self.assertEqual((await self.send("不同请求", selection, rid)).status_code, 409)
        restored = (await self.client.get(f"/api/agent/sessions/{self.sid}")).json()
        self.assertEqual(restored, saved)

    async def test_filter_patch_compare_and_stale_selection(self):
        old = await self.recommend()
        self.queue.extend(
            [
                [
                    (
                        "update_preferences",
                        {"patch": {"city": "杭州", "age_min": 24, "age_max": 29}},
                    ),
                    ("search_candidates", {}),
                ],
                "这些都符合同城与年龄要求。",
            ]
        )
        events = self.events(await self.send("只看同城，24至29岁"))
        current = next(e["session"] for e in events if e["type"] == "state")
        self.assertTrue(
            all(
                c["city"] == "杭州" and 24 <= c["age"] <= 29
                for c in current["candidates"]
            )
        )
        self.assertEqual(
            (
                await self.send(
                    "选旧卡",
                    {
                        "candidate_id": old["candidates"][0]["id"],
                        "revision": old["revision"],
                    },
                )
            ).status_code,
            409,
        )
        ids = [c["id"] for c in current["candidates"][:2]]
        self.queue.extend(
            [[("compare_candidates", {"candidate_ids": ids})], "可以比较见面频率。"]
        )
        result = self.events(await self.send("比较前两位"))
        self.assertTrue(
            any(
                e["type"] == "card" and e["card"]["component"] == "comparison"
                for e in result
            )
        )
        self.queue.extend(
            [
                [
                    (
                        "update_preferences",
                        {"patch": {"age_min": None, "age_max": None}},
                    ),
                    ("search_candidates", {}),
                ],
                "保留杭州条件。",
            ]
        )
        relaxed = next(
            e["session"]
            for e in self.events(await self.send("年龄不限"))
            if e["type"] == "state"
        )
        self.assertEqual(relaxed["preferences"]["city"], "杭州")
        self.assertIsNone(relaxed["preferences"]["age_max"])

    async def test_empty_does_not_silently_relax(self):
        await self.recommend()
        self.queue.extend(
            [
                [
                    ("update_preferences", {"patch": {"age_min": 79}}),
                    ("search_candidates", {}),
                ],
                "没有符合的候选，请选择如何放宽。",
            ]
        )
        events = self.events(await self.send("只看79岁以上"))
        state = next(e["session"] for e in events if e["type"] == "state")
        self.assertEqual(state["candidates"], [])
        self.assertEqual(state["preferences"]["age_min"], 79)
        self.assertTrue(
            any(
                e["type"] == "card" and e["card"]["component"] == "empty"
                for e in events
            )
        )

    async def test_model_failure_rolls_back_preferences_and_results(self):
        old = await self.recommend()
        self.queue.extend(
            [
                [("update_preferences", {"patch": {"city": "上海"}})],
                ModelError("连接中断"),
            ]
        )
        events = self.events(await self.send("改为上海"))
        self.assertEqual(events[-1]["type"], "error")
        current = (await self.client.get(f"/api/agent/sessions/{self.sid}")).json()
        self.assertEqual(old, current)
        self.queue.extend(["可以重试。"])
        self.assertEqual(self.events(await self.send())[-1]["type"], "done")

    async def test_invalid_tool_arguments_do_not_modify_state(self):
        old = await self.recommend()
        self.queue.extend(
            [
                [
                    ("update_preferences", {"patch": {"age_min": 40, "age_max": 20}}),
                    ("compare_candidates", {"candidate_ids": [999, 998]}),
                ],
                "请换一组条件。",
            ]
        )
        events = self.events(await self.send("测试错误参数"))
        self.assertEqual(
            len(
                [
                    e
                    for e in events
                    if e["type"] == "tool_end" and e["status"] == "error"
                ]
            ),
            2,
        )
        current = next(e["session"] for e in events if e["type"] == "state")
        self.assertEqual(current["preferences"], old["preferences"])
        self.assertEqual(current["revision"], old["revision"])

    async def test_date_requires_explicit_selection(self):
        state = await self.recommend()
        response = await self.client.post(
            "/api/date/plan",
            json={
                "session_id": self.sid,
                "candidate_id": state["candidates"][0]["id"],
                "budget": 100,
                "start": "18:00",
            },
        )
        self.assertEqual(response.status_code, 409)

    async def test_concurrent_request_rejected_and_cancel_releases(self):
        started = asyncio.Event()

        async def wait():
            started.set()
            await asyncio.sleep(60)

        self.queue.append(wait)
        task = asyncio.create_task(self.send())
        await asyncio.wait_for(started.wait(), 2)
        self.assertEqual((await self.send("另一条")).status_code, 409)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.store.get(self.sid)["turns"], [])
        self.queue.append("停止后可以继续。")
        self.assertEqual(self.events(await self.send())[-1]["type"], "done")

    async def test_change_filters_clears_selection_and_new_batch_excludes_seen(self):
        old = await self.recommend()
        await self.send(
            "选这位",
            {"candidate_id": old["candidates"][0]["id"], "revision": old["revision"]},
        )
        self.queue.extend(
            [[("search_candidates", {"exclude_seen": True})], "新一批候选。"]
        )
        current = next(
            e["session"]
            for e in self.events(await self.send("换一批"))
            if e["type"] == "state"
        )
        self.assertIsNone(current["selected_id"])
        self.assertFalse(
            {c["id"] for c in old["candidates"]}
            & {c["id"] for c in current["candidates"]}
        )

    async def test_date_tools_and_latest_plan_restored(self):
        from backend.domain.schemas import DateChoice, FeedbackResult

        state = await self.recommend()
        candidate = state["candidates"][0]
        await self.send(
            "选这位", {"candidate_id": candidate["id"], "revision": state["revision"]}
        )

        async def structured(system, data, schema, validate=None):
            if schema is DateChoice:
                plan = data["recommended_combinations"][0]
                result = DateChoice(
                    meal_id=plan["meal_id"],
                    activity_id=plan["activity_id"],
                    drink_id=plan["drink_id"],
                    reason="预算合适",
                    conflict_detected=False,
                    conflict_description="",
                )
            else:
                result = FeedbackResult(explanation="见面频率可以商量")
            if validate:
                validate(result)
            return result

        async def stream(*args):
            yield "行程说明"

        with (
            patch.object(self.model, "structured", structured),
            patch.object(self.model, "stream", stream),
        ):
            response = await self.client.post(
                "/api/date/plan",
                json={
                    "session_id": self.sid,
                    "candidate_id": candidate["id"],
                    "budget": 30,
                    "start": "20:00",
                },
            )
        events = self.events(response)
        self.assertEqual(events[-1]["type"], "done")
        self.assertTrue(
            any(
                e["type"] == "tool_start" and e["name"] == "validate_budget_and_time"
                for e in events
            )
        )
        saved = (await self.client.get(f"/api/agent/sessions/{self.sid}")).json()
        self.assertEqual(saved["latest_date"]["summary"], "行程说明")
        self.assertEqual(
            sum(p["cost"] for p in saved["latest_date"]["result"]["plan"]), 27
        )
        self.queue.extend(
            [
                [
                    ("update_preferences", {"patch": {"city": "上海"}}),
                    ("search_candidates", {}),
                ],
                "新的候选。",
            ]
        )
        changed = next(
            e["session"]
            for e in self.events(await self.send("换上海"))
            if e["type"] == "state"
        )
        self.assertNotIn("latest_date", changed)
