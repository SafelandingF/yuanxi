from ..domain.matching import search_candidates
from ..domain.ports import Repository
from ..domain.schemas import Preferences
from .cards import card
from .profile import ProfileAgent


class ToolExecutor:
    def __init__(self, repository: Repository, profile_agent: ProfileAgent):
        self.repository = repository
        self.profile_agent = profile_agent

    async def execute(self, name, args, state):
        if not isinstance(args, dict):
            raise TypeError("工具参数应为对象")
        profile = state["profile"]
        if name == "analyze_profile":
            if args:
                raise ValueError("画像工具无需参数")
            if not state["portrait"]:
                state["portrait"] = await self.profile_agent.analyze(profile)
            return state["portrait"], card("profile", state["portrait"], state)
        if name == "update_preferences":
            if set(args) != {"patch"}:
                raise ValueError("请提供patch")
            patch = Preferences.model_validate(args["patch"]).model_dump(
                exclude_unset=True
            )
            state["preferences"] = Preferences.model_validate(
                {**state["preferences"], **patch}
            ).model_dump()
            state["revision"] += 1
            state["candidates"], state["selected_id"], state["seen"] = [], None, []
            state.pop("latest_date", None)
            return state["preferences"], card(
                "preferences", state["preferences"], state
            )
        if name == "search_candidates":
            if set(args) - {"exclude_seen"} or (
                "exclude_seen" in args and type(args["exclude_seen"]) is not bool
            ):
                raise ValueError("exclude_seen需为布尔值")
            if not state["portrait"]:
                raise ValueError("请先调用analyze_profile")
            result = search_candidates(
                profile,
                state["preferences"],
                self.repository.candidates(),
                state["seen"],
                args.get("exclude_seen", False),
            )
            ranked = result["candidates"]
            state["revision"] += 1
            state["candidates"], state["selected_id"] = ranked, None
            state.pop("latest_date", None)
            state["seen"] = list(set(state["seen"]) | {c["id"] for c in ranked})
            state["known"].update({str(c["id"]): c for c in ranked})
            return result, card("candidates" if ranked else "empty", result, state)
        if name == "compare_candidates":
            ids = args.get("candidate_ids", [])
            if (
                set(args) != {"candidate_ids"}
                or not isinstance(ids, list)
                or not 2 <= len(ids) <= 3
                or len(set(ids)) != len(ids)
                or any(type(i) is not int or str(i) not in state["known"] for i in ids)
            ):
                raise ValueError("只能比较2至3位已展示且不重复的候选")
            result = {"candidates": [state["known"][str(i)] for i in ids]}
            return result, card("comparison", result, state)
        raise ValueError("未知工具")
