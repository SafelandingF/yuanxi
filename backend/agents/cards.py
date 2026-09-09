CARD_COMPONENTS = {
    "profile",
    "preferences",
    "candidates",
    "comparison",
    "selection",
    "empty",
}


def card(component, props, state):
    if component not in CARD_COMPONENTS:
        raise ValueError("不支持的交互卡片")
    return {"component": component, "props": props, "revision": state["revision"]}
