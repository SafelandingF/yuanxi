from ..domain.schemas import Preferences


def tool(name, description, properties, required=()):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(required),
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    tool("analyze_profile", "读取并分析已填写的个人资料，首次推荐前必须调用。", {}),
    tool(
        "update_preferences",
        "按用户明确要求修改候选筛选条件，未提及字段不传；null/空兴趣表示取消该限制。不改变用户个人资料。修改后需重新检索。兴趣为至少符合其中一项。",
        {"patch": Preferences.model_json_schema()},
        ["patch"],
    ),
    tool(
        "search_candidates",
        "按当前条件查询本地虚构候选库并返回最多3位。换一批时exclude_seen=true，绝不自动放宽条件。",
        {"exclude_seen": {"type": "boolean"}},
    ),
    tool(
        "compare_candidates",
        "比较已展示候选的真实资料及差异，生成可交互对比卡。",
        {
            "candidate_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 3,
            }
        },
        ["candidate_ids"],
    ),
]
