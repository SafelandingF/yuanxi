import json
import time
from uuid import uuid4

from pydantic import ValidationError

from ..domain.errors import ModelError
from ..domain.events import event
from ..domain.ports import LanguageModel
from ..domain.schemas import ChatRequest
from .cards import card
from .definitions import TOOLS
from .prompts import SYSTEM
from .tools import ToolExecutor


class MatchingAgent:
    def __init__(self, model: LanguageModel, tools: ToolExecutor):
        self.model = model
        self.tools = tools

    async def run(self, state: dict, body: ChatRequest):
        turn = {
            "id": body.request_id,
            "request": body.model_dump(exclude={"request_id"}),
            "user": body.text,
            "parts": [],
        }

        def record(item):
            if (
                item["type"] == "delta"
                and turn["parts"]
                and (turn["parts"][-1]["type"] == "text")
            ):
                turn["parts"][-1]["text"] += item["text"]
            elif item["type"] == "delta":
                turn["parts"].append({"type": "text", "text": item["text"]})
            elif item["type"] == "tool_end":
                part = next(p for p in turn["parts"] if p.get("id") == item["id"])
                part.update(item)
            else:
                turn["parts"].append(item)
            return event(item["type"], **{k: v for k, v in item.items() if k != "type"})

        if body.selection:
            candidate = next(
                c for c in state["candidates"] if c["id"] == body.selection.candidate_id
            )
            turn["user"] = "我选择 " + candidate["name"]
            cid = str(uuid4())
            yield record(
                {
                    "type": "tool_start",
                    "id": cid,
                    "name": "select_candidate",
                    "label": "确认你选择的对象",
                    "input": {"candidate_id": candidate["id"]},
                }
            )
            if state["selected_id"] != candidate["id"]:
                state.pop("latest_date", None)
            state["selected_id"] = candidate["id"]
            yield record(
                {
                    "type": "tool_end",
                    "id": cid,
                    "status": "success",
                    "summary": "已确认 " + candidate["name"],
                    "duration_ms": 0,
                }
            )
            yield record(
                {
                    "type": "card",
                    "card": card("selection", {"candidate": candidate}, state),
                }
            )
            message = "已记下你的选择。接下来可以一起安排预算、口味和见面时间；也可以继续聊聊，换一个更合适的人。"
            yield record({"type": "delta", "text": message})
            state["history"].extend(
                [
                    {"role": "user", "content": turn["user"]},
                    {"role": "assistant", "content": message},
                ]
            )
        else:
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM
                    + "\n当前可信状态："
                    + json.dumps(
                        {
                            k: state[k]
                            for k in (
                                "profile",
                                "preferences",
                                "selected_id",
                                "candidates",
                            )
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
            messages += state["history"] + [{"role": "user", "content": body.text}]
            history_start = len(messages) - 1
            for iteration in range(6):
                message = None
                async for item in self.model.agent_step(messages, TOOLS):
                    if item["type"] == "delta":
                        yield record(item)
                    else:
                        message = item["message"]
                if message is None:
                    raise ModelError("模型未返回完整回复")
                messages.append(message)
                calls = message.get("tool_calls", [])
                if not calls:
                    break
                if len(calls) > 5:
                    raise ModelError("本轮工具请求过多，请简化要求后重试")
                for call in calls:
                    name, cid = (call["function"]["name"], call["id"])
                    labels = {
                        "analyze_profile": "提炼你的关系画像",
                        "update_preferences": "更新本次筛选条件",
                        "search_candidates": "检索本地虚构候选",
                        "compare_candidates": "比较候选的共同点与差异",
                    }
                    started = time.monotonic()
                    try:
                        args = json.loads(call["function"]["arguments"])
                    except ValueError:
                        args = None
                    yield record(
                        {
                            "type": "tool_start",
                            "id": cid,
                            "name": name,
                            "label": labels.get(name, "校验工具请求"),
                            "input": args,
                        }
                    )
                    try:
                        result, ui = await self.tools.execute(name, args, state)
                        summary = (
                            f"筛选到 {result['matched']} 人，展示 {len(result['candidates'])} 人"
                            if name == "search_candidates"
                            else "已完成，可展开查看输入与结果"
                        )
                        yield record(
                            {
                                "type": "tool_end",
                                "id": cid,
                                "status": "success",
                                "summary": summary,
                                "duration_ms": round(
                                    (time.monotonic() - started) * 1000
                                ),
                                "output": result,
                            }
                        )
                        yield record({"type": "card", "card": ui})
                    except (ValueError, ValidationError, TypeError):
                        result = {
                            "error": "工具参数无效，请检查字段、年龄范围及候选编号后重新调用。"
                        }
                        yield record(
                            {
                                "type": "tool_end",
                                "id": cid,
                                "status": "error",
                                "summary": result["error"],
                                "duration_ms": round(
                                    (time.monotonic() - started) * 1000
                                ),
                            }
                        )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": cid,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
            else:
                raise ModelError("本轮处理步骤较多，已暂停，请拆分要求后重试")
            state["history"].extend(messages[history_start:])
        state["turns"].append(turn)
        if len(state["turns"]) > 30:
            raise ModelError("这段对话已达30轮，请重新保存资料开启新对话")
