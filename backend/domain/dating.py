from .catalog import ACTIVITIES, DRINKS, MEALS


def available_meals(candidate, body):
    limit = min(body.budget, candidate["budget"])
    meals = [
        m
        for m in MEALS
        if m["cost"] + 10 <= limit
        and (
            (candidate["food"] != "素食友好" and "素食" not in body.food_restrictions)
            or m["id"] != "tomato"
        )
    ]
    return limit, meals


def validate_choice(choice, meals, limit):
    meal = next((x for x in meals if x["id"] == choice.meal_id), None)
    activity = next((x for x in ACTIVITIES if x["id"] == choice.activity_id), None)
    drink = next((x for x in DRINKS if x["id"] == choice.drink_id), None)
    if (
        not meal
        or not activity
        or not drink
        or meal["cost"] + activity["cost"] + drink["cost"] > limit
    ):
        raise ValueError("invalid plan")


def build_itinerary(choice, meals, start_time):
    hours, minutes = map(int, start_time.split(":"))
    start = hours * 60 + minutes
    plan = []
    for kind, item_id, options, offset in [
        ("food", choice.meal_id, meals, 0),
        ("walk", choice.activity_id, ACTIVITIES, 75),
        ("coffee", choice.drink_id, DRINKS, 125),
    ]:
        item = next(x for x in options if x["id"] == item_id)
        time = start + offset
        plan.append(
            {
                "kind": kind,
                "time": f"{time // 60:02}:{time % 60:02}",
                **{k: v for k, v in item.items() if k != "id"},
            }
        )
    return plan


def frequency_conflict(profile, candidate):
    frequency = {"每周 2–3 次": 3, "每周 1 次": 2, "每月 1–2 次": 1}
    return (
        abs(frequency[profile["companionship"]] - frequency[candidate["companionship"]])
        == 2
    )
