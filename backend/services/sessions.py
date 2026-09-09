import copy
from uuid import uuid4

from ..agents.matching import MatchingAgent
from ..domain.errors import Conflict, NotFound
from ..domain.events import event
from ..domain.ports import Repository
from ..domain.schemas import ChatRequest, Preferences, Profile


def public(session):
    return {k: v for k, v in session.items() if k != "history"}


class SessionService:
    def __init__(self, repository: Repository, agent: MatchingAgent):
        self.repository = repository
        self.agent = agent
        self.active: set[str] = set()

    def load(self, sid: str):
        state = self.repository.get(sid)
        if not state or state.get("kind") != "agent":
            raise NotFound("对话不存在，请重新保存个人资料")
        return state

    def get(self, sid: str):
        return public(self.load(sid))

    def create(self, profile: Profile):
        sid = str(uuid4())
        state = {
            "kind": "agent",
            "session_id": sid,
            "profile": profile.model_dump(),
            "portrait": None,
            "preferences": Preferences().model_dump(),
            "revision": 0,
            "candidates": [],
            "known": {},
            "seen": [],
            "selected_id": None,
            "turns": [],
            "history": [],
        }
        self.repository.save(sid, state)
        return public(state)

    def chat(self, sid: str, body: ChatRequest):
        # 工具只修改副本；模型正常结束后才保存整轮对话。
        state = copy.deepcopy(self.load(sid))
        if sid in self.active:
            raise Conflict("这段对话还在处理中，请稍后重试")
        existing = next((t for t in state["turns"] if t["id"] == body.request_id), None)
        if existing:
            if existing.get("request") != body.model_dump(exclude={"request_id"}):
                raise Conflict("消息标识重复，请重新发送")

            async def replay():
                yield event("state", session=public(state))
                yield event("done")

            return replay()
        if len(state["turns"]) >= 30:
            raise Conflict("这段对话已达30轮，请重新保存资料开启新对话")
        if body.selection and (
            body.selection.revision != state["revision"]
            or body.selection.candidate_id not in [c["id"] for c in state["candidates"]]
        ):
            raise Conflict("这张候选卡已更新，请从最新推荐中选择")
        self.active.add(sid)
        return self._run(sid, state, body)

    async def _run(self, sid, state, body):
        runner = self.agent.run(state, body)
        try:
            async for item in runner:
                yield item
            # 对话期间约会可能已完成，保留同一候选版本的新结果。
            latest = self.repository.get(sid)
            if (
                latest
                and latest.get("revision") == state["revision"]
                and latest.get("selected_id") == state["selected_id"]
                and latest.get("latest_date")
            ):
                state["latest_date"] = latest["latest_date"]
            self.repository.save(sid, state)
            yield event("state", session=public(state))
            yield event("done")
        finally:
            await runner.aclose()
            self.active.discard(sid)
