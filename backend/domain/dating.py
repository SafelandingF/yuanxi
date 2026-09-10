from collections import Counter

from .catalog import ACTIVITIES, DRINKS, MEALS

SPENDING_RATIOS = {
    "性价比优先": 0.55,
    "均衡安排": 0.75,
    "体验优先": 0.90,
}
PREFERENCE_CATEGORY = {
    "想吃锅类": "锅类",
    "偏爱简餐": "简餐",
    "偏爱素食": "素食",
}


def available_meals(candidate, body):
    """Apply dietary requirements before an option is ever sent to the model."""
    limit = min(body.budget, candidate["budget"])
    vegetarian = "素食" in body.food_restrictions or "素食" in candidate["food"]
    avoid_spicy = "不吃辣" in body.food_restrictions or "不太辣" in candidate["food"]
    cheapest_finish = min(x["cost"] for x in DRINKS)
    meals = [
        meal
        for meal in MEALS
        if meal["cost"] + cheapest_finish <= limit
        and (not vegetarian or meal["vegetarian_ok"])
        and (not avoid_spicy or not meal["spicy"])
    ]

    preferred = PREFERENCE_CATEGORY.get(body.meal_preference)
    if preferred:
        matching = [meal for meal in meals if preferred in meal["categories"]]
        # A preference should guide the plan, but must not make a low-budget
        # request impossible when no matching item fits.
        if matching:
            meals = matching
    return limit, meals


def recommended_combinations(profile, candidate, body, meals, limit):
    """Rank valid local combinations before asking the LLM to explain one."""
    target = round(limit * SPENDING_RATIOS[body.spending_style])
    traits = set(profile["interests"]) | set(candidate["interests"])
    traits.update((profile["rhythm"], candidate["rhythm"]))
    if "爱尝鲜" in candidate["food"]:
        traits.add("爱尝鲜")
    avoided = set(body.avoid_ids)
    ranked = []

    for meal in meals:
        for activity in ACTIVITIES:
            for drink in DRINKS:
                items = (meal, activity, drink)
                total = sum(item["cost"] for item in items)
                if total > limit:
                    continue
                tags = set().union(*(set(item.get("tags", [])) for item in items))
                matched = sorted(tags & traits)
                repeated = sum(item["id"] in avoided for item in items)
                duration = sum(item["duration_minutes"] for item in items) + 30
                affinity = len(matched) * 12
                experience = 8 if body.spending_style == "体验优先" and "体验" in tags else 0
                late_penalty = 12 if body.start >= "19:00" and duration > 230 else 0
                score = (
                    120
                    - abs(total - target) * 1.4
                    + affinity
                    + experience
                    - repeated * 70
                    - late_penalty
                )
                ranked.append(
                    (
                        score,
                        {
                            "meal_id": meal["id"],
                            "activity_id": activity["id"],
                            "drink_id": drink["id"],
                            "total": total,
                            "duration_minutes": duration,
                            "matched_tags": matched,
                        },
                    )
                )

    ranked.sort(
        key=lambda item: (
            -item[0],
            abs(item[1]["total"] - target),
            item[1]["meal_id"],
            item[1]["activity_id"],
            item[1]["drink_id"],
        )
    )
    # Keep the prompt varied instead of filling it with near-identical versions
    # of one meal. Two combinations per meal is enough for meaningful choice.
    counts = Counter()
    choices = []
    for _, option in ranked:
        if counts[option["meal_id"]] >= 2:
            continue
        counts[option["meal_id"]] += 1
        choices.append(option)
        if len(choices) == 12:
            break
    return target, choices


def validate_choice(choice, meals, limit, combinations=None):
    meal = next((x for x in meals if x["id"] == choice.meal_id), None)
    activity = next((x for x in ACTIVITIES if x["id"] == choice.activity_id), None)
    drink = next((x for x in DRINKS if x["id"] == choice.drink_id), None)
    if not meal:
        allowed = ", ".join(x["id"] for x in meals)
        raise ValueError(f"meal_id 必须是以下值之一：{allowed}")
    if not activity:
        allowed = ", ".join(x["id"] for x in ACTIVITIES)
        raise ValueError(f"activity_id 必须是以下值之一：{allowed}")
    if not drink:
        allowed = ", ".join(x["id"] for x in DRINKS)
        raise ValueError(f"drink_id 必须是以下值之一：{allowed}")
    total = meal["cost"] + activity["cost"] + drink["cost"]
    if total > limit:
        raise ValueError(f"所选组合人均 {total} 元，必须不超过 {limit} 元")
    if combinations is not None:
        selected = (choice.meal_id, choice.activity_id, choice.drink_id)
        allowed = {
            (option["meal_id"], option["activity_id"], option["drink_id"])
            for option in combinations
        }
        if selected not in allowed:
            raise ValueError("三个 id 必须原样来自同一个 recommended_combinations 组合")


def build_itinerary(choice, meals, start_time):
    hours, minutes = map(int, start_time.split(":"))
    cursor = hours * 60 + minutes
    plan = []
    selections = [
        ("food", choice.meal_id, meals),
        ("walk", choice.activity_id, ACTIVITIES),
        ("coffee", choice.drink_id, DRINKS),
    ]
    for index, (kind, item_id, options) in enumerate(selections):
        item = next(x for x in options if x["id"] == item_id)
        plan.append(
            {
                "catalog_id": item["id"],
                "kind": kind,
                "time": f"{(cursor // 60) % 24:02}:{cursor % 60:02}",
                "title": item["title"],
                "detail": item["detail"],
                "cost": item["cost"],
                "duration_minutes": item["duration_minutes"],
            }
        )
        cursor += item["duration_minutes"]
        if index < len(selections) - 1:
            cursor += 15
    return plan


def frequency_conflict(profile, candidate):
    frequency = {"每周 2–3 次": 3, "每周 1 次": 2, "每月 1–2 次": 1}
    return (
        abs(frequency[profile["companionship"]] - frequency[candidate["companionship"]])
        == 2
    )
