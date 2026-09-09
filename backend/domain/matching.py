def score(profile, candidate):
    return min(
        98,
        35
        + min(24, len(set(profile["interests"]) & set(candidate["interests"])) * 8)
        + (15 if profile["rhythm"] == candidate["rhythm"] else 0)
        + (10 if profile["city"] == candidate["city"] else 0)
        + (10 if profile["goal"] == candidate["goal"] else 0)
        + max(0, 6 - abs(profile["age"] - candidate["age"])),
    )


def search_candidates(profile, prefs, pool, seen, exclude_seen=False):
    matched = [
        c
        for c in pool
        if (not prefs["city"] or c["city"] == prefs["city"])
        and (not prefs["age_min"] or c["age"] >= prefs["age_min"])
        and (not prefs["age_max"] or c["age"] <= prefs["age_max"])
        and (
            not prefs["interests"]
            or bool(set(c["interests"]) & set(prefs["interests"]))
        )
        and (not prefs["companionship"] or c["companionship"] == prefs["companionship"])
        and (not prefs["goal"] or c["goal"] == prefs["goal"])
    ]
    eligible = [c for c in matched if not exclude_seen or c["id"] not in seen]
    ranked = sorted(
        [{**c, "score": score(profile, c)} for c in eligible],
        key=lambda c: (-c["score"], c["id"]),
    )[:3]
    for c in ranked:
        common = sorted(set(profile["interests"]) & set(c["interests"]))
        c["strengths"] = (
            (["共同兴趣：" + "、".join(common)] if common else [])
            + (["同城，见面更方便"] if profile["city"] == c["city"] else [])
            + (["生活节奏一致"] if profile["rhythm"] == c["rhythm"] else [])
        )
        c["conflicts"] = (
            (
                [
                    "见面频率：你期待"
                    + profile["companionship"]
                    + "，对方"
                    + c["companionship"]
                ]
                if profile["companionship"] != c["companionship"]
                else []
            )
            + (["不同城市，需要商量出行"] if profile["city"] != c["city"] else [])
            + (
                ["关系目标不同：对方希望" + c["goal"]]
                if profile["goal"] != c["goal"]
                else []
            )
        )
        c["explanation"] = (
            "基于共同兴趣、城市、生活节奏、关系目标与年龄差计算的参考适配分。"
        )
    result = {
        "candidates": ranked,
        "total": len(pool),
        "matched": len(matched),
        "remaining": len(eligible),
        "preferences": prefs,
    }
    return result
