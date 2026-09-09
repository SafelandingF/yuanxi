from typing import Any

Event = dict[str, Any]


def event(kind: str, **data: Any) -> Event:
    """Agent 输出业务事件；如何编码为 SSE 由接口层决定。"""
    return {"type": kind, **data}
