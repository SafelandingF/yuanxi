import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from backend.core.config import ModelConfig
from backend.domain.errors import ModelError
from backend.domain.schemas import FeedbackResult
from backend.infrastructure.ark import Ark


class ArkContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ark = Ark(ModelConfig(api_key="test-only"))
        await self.ark.client.aclose()

    async def asyncTearDown(self):
        await self.ark.client.aclose()

    def client(self, handler):
        self.ark.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def test_retries_limited_status(self):
        calls = []

        async def handler(request):
            calls.append(request)
            if len(calls) < 3:
                return httpx.Response(429)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps({"explanation": "已检查"})
                            },
                        }
                    ]
                },
            )

        self.client(handler)
        with patch("backend.infrastructure.ark.asyncio.sleep", return_value=None):
            result = await self.ark.structured("反馈", {}, FeedbackResult)
        self.assertEqual(result.explanation, "已检查")
        self.assertEqual(len(calls), 3)

    async def test_invalid_json_retries_once(self):
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": "not json"}}
                    ]
                },
            )

        self.client(handler)
        with self.assertRaises(ModelError):
            await self.ark.structured("反馈", {}, FeedbackResult)
        self.assertEqual(len(calls), 2)

    async def test_truncated_stream_not_success(self):
        async def handler(request):
            return httpx.Response(
                200, text='data: {"choices":[{"delta":{"content":"部分结果"}}]}\n\n'
            )

        self.client(handler)
        chunks = []
        with self.assertRaises(ModelError):
            async for chunk in self.ark.stream("说明", {}):
                chunks.append(chunk)
        self.assertEqual(chunks, ["部分结果"])

    async def test_abort_cancels_upstream(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def handler(request):
            started.set()
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        self.client(handler)
        task = asyncio.create_task(self.ark.structured("说明", {}, FeedbackResult))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(cancelled.is_set())

    async def test_successful_stream(self):
        async def handler(request):
            return httpx.Response(
                200,
                text='data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n',
            )

        self.client(handler)
        self.assertEqual(
            "".join([x async for x in self.ark.stream("说明", {})]), "你好"
        )

    async def test_auth_error_does_not_echo_provider_body(self):
        async def handler(request):
            return httpx.Response(401, text="test-only")

        self.client(handler)
        with self.assertRaises(ModelError) as ctx:
            await self.ark.structured("说明", {}, FeedbackResult)
        self.assertNotIn("test-only", str(ctx.exception))

    async def test_native_tool_deltas_and_reasoning_not_exposed(self):
        frames = [
            {
                "delta": {
                    "reasoning_content": "private reasoning",
                    "content": "我会先查询。",
                }
            },
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call1",
                            "function": {
                                "name": "search_candidates",
                                "arguments": '{"exclude_',
                            },
                        }
                    ]
                }
            },
            {
                "delta": {
                    "tool_calls": [
                        {"index": 0, "function": {"arguments": 'seen":true}'}}
                    ]
                }
            },
            {"delta": {}, "finish_reason": "tool_calls"},
        ]

        async def handler(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["tool_choice"], "auto")
            return httpx.Response(
                200,
                text="".join(
                    "data: " + json.dumps({"choices": [f]}) + "\n\n" for f in frames
                )
                + "data: [DONE]\n\n",
            )

        self.client(handler)
        items = [
            item
            async for item in self.ark.agent_step(
                [{"role": "user", "content": "找找"}], []
            )
        ]
        self.assertNotIn("private reasoning", json.dumps(items))
        call = items[-1]["message"]["tool_calls"][0]
        self.assertEqual(call["id"], "call1")
        self.assertEqual(
            json.loads(call["function"]["arguments"]), {"exclude_seen": True}
        )

    async def test_native_truncated_call_is_error(self):
        async def handler(request):
            return httpx.Response(
                200,
                text='data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c","function":{"name":"search_candidates","arguments":"{"}}]},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n',
            )

        self.client(handler)
        with self.assertRaises(ModelError):
            _ = [item async for item in self.ark.agent_step([], [])]


if __name__ == "__main__":
    unittest.main()
