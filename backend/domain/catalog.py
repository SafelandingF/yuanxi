"""Fictional per-person options for the classroom demo."""

MEALS = [
    {"id": "simple", "title": "一起吃一份家常简餐", "detail": "清淡家常搭配，适合把注意力留给聊天", "cost": 22, "duration_minutes": 60, "categories": ["简餐"], "tags": ["安静", "规律慢生活"], "vegetarian_ok": True, "spicy": False},
    {"id": "noodles", "title": "选一家舒服的面馆", "detail": "暖胃又不拘谨，可选择清汤与素食浇头", "cost": 28, "duration_minutes": 55, "categories": ["简餐"], "tags": ["性价比", "规律慢生活"], "vegetarian_ok": True, "spicy": False},
    {"id": "dumplings", "title": "分享一份手工水饺", "detail": "选择清淡馅料，轻松吃饭也方便慢慢聊天", "cost": 32, "duration_minutes": 60, "categories": ["简餐"], "tags": ["安静", "性价比"], "vegetarian_ok": True, "spicy": False},
    {"id": "vegetarian", "title": "尝一顿精致蔬食", "detail": "全素组合，口味清爽，适合安静地相互了解", "cost": 42, "duration_minutes": 70, "categories": ["素食", "简餐"], "tags": ["安静", "看展", "规律慢生活"], "vegetarian_ok": True, "spicy": False},
    {"id": "tomato", "title": "一顿温暖的番茄锅", "detail": "清淡不辣，可选择素食锅底", "cost": 45, "duration_minutes": 75, "categories": ["锅类"], "tags": ["温暖", "规律慢生活"], "vegetarian_ok": True, "spicy": False},
    {"id": "brunch", "title": "找间明亮小店吃早午餐", "detail": "轻食、主食都能选，适合周末不赶时间的见面", "cost": 52, "duration_minutes": 75, "categories": ["简餐"], "tags": ["咖啡", "摄影", "自由随性"], "vegetarian_ok": True, "spicy": False},
    {"id": "mushroom_pot", "title": "分享一锅菌菇小火锅", "detail": "鲜香但不辛辣，可选择全素拼盘", "cost": 58, "duration_minutes": 85, "categories": ["锅类", "素食"], "tags": ["温暖", "旅行"], "vegetarian_ok": True, "spicy": False},
    {"id": "local_cuisine", "title": "尝一顿本地风味菜", "detail": "用几道招牌家常菜打开关于城市和旅行的话题", "cost": 62, "duration_minutes": 80, "categories": ["正餐"], "tags": ["旅行", "爱尝鲜"], "vegetarian_ok": False, "spicy": False},
    {"id": "japanese", "title": "安静地吃一顿日式定食", "detail": "一人一份不尴尬，环境相对安静", "cost": 72, "duration_minutes": 75, "categories": ["正餐"], "tags": ["安静", "摄影"], "vegetarian_ok": False, "spicy": False},
    {"id": "barbecue", "title": "一起尝尝炭火烤肉", "detail": "气氛热闹，建议提前确认口味和无辣选择", "cost": 76, "duration_minutes": 90, "categories": ["正餐"], "tags": ["热闹", "爱尝鲜"], "vegetarian_ok": False, "spicy": True},
    {"id": "western", "title": "留出时间吃一顿西式晚餐", "detail": "节奏舒缓，适合想认真聊聊的晚上", "cost": 88, "duration_minutes": 95, "categories": ["正餐"], "tags": ["安静", "电影", "体验"], "vegetarian_ok": True, "spicy": False},
]

ACTIVITIES = [
    {"id": "walk", "title": "沿着街区慢慢走一段", "detail": "轻松散步约 40 分钟；下雨可改室内商场", "cost": 0, "duration_minutes": 40, "tags": ["散步", "安静", "规律慢生活"]},
    {"id": "book", "title": "在书店交换喜欢的一页", "detail": "免费逛书店，不安排额外购物", "cost": 0, "duration_minutes": 35, "tags": ["阅读", "安静", "规律慢生活"]},
    {"id": "photo_walk", "title": "来一次城市摄影散步", "detail": "选一段好走的街区，互相记录喜欢的画面", "cost": 12, "duration_minutes": 60, "tags": ["摄影", "散步", "旅行"]},
    {"id": "cycling", "title": "沿安全绿道轻松骑行", "detail": "按共享单车与基础装备估价，量力而行", "cost": 20, "duration_minutes": 70, "tags": ["运动", "旅行", "自由随性"]},
    {"id": "board_game", "title": "合作玩一局轻量桌游", "detail": "选择规则简单的双人游戏，避免过强对抗", "cost": 35, "duration_minutes": 90, "tags": ["游戏", "热闹", "自由随性"]},
    {"id": "badminton", "title": "打一场轻松的羽毛球", "detail": "包含场地与基础用具的虚构估价", "cost": 38, "duration_minutes": 75, "tags": ["运动", "活力"]},
    {"id": "movie", "title": "挑一部都感兴趣的电影", "detail": "按普通影厅票价估算，看完还有话题可聊", "cost": 45, "duration_minutes": 120, "tags": ["电影", "安静"]},
    {"id": "exhibition", "title": "一起看一场小型展览", "detail": "按常规展览票价估算，边看边交换感受", "cost": 55, "duration_minutes": 90, "tags": ["看展", "摄影", "安静"]},
    {"id": "pottery", "title": "完成一次双人陶艺体验", "detail": "按基础体验课程估价，适合一起完成小作品", "cost": 78, "duration_minutes": 100, "tags": ["体验", "摄影", "安静"]},
    {"id": "live_music", "title": "听一场小型现场音乐演出", "detail": "按普通入场票估价，选择音量舒适的场次", "cost": 85, "duration_minutes": 100, "tags": ["音乐", "热闹", "体验"]},
]

DRINKS = [
    {"id": "water", "title": "带一瓶水，留点机动时间", "detail": "不刻意追加消费，按实际需要决定是否停留", "cost": 5, "duration_minutes": 20, "tags": ["性价比", "运动"]},
    {"id": "tea", "title": "喝杯茶，聊聊今天", "detail": "无糖茶饮，留一点安静的时间", "cost": 12, "duration_minutes": 40, "tags": ["安静", "阅读", "规律慢生活"]},
    {"id": "juice", "title": "用一杯果汁稍作休息", "detail": "清爽无酒精，也方便照顾晚间睡眠", "cost": 18, "duration_minutes": 35, "tags": ["运动", "自由随性"]},
    {"id": "coffee", "title": "用一杯热饮收藏今天", "detail": "可选择无咖啡因热饮", "cost": 22, "duration_minutes": 45, "tags": ["咖啡", "安静"]},
    {"id": "dessert", "title": "分享一份小甜点", "detail": "选择一份分食，给行程留一个轻松收尾", "cost": 28, "duration_minutes": 40, "tags": ["摄影", "体验", "自由随性"]},
    {"id": "dessert_set", "title": "坐下来享用甜品与饮品", "detail": "按一份甜品加一杯饮品的组合估价", "cost": 38, "duration_minutes": 50, "tags": ["咖啡", "摄影", "体验"]},
]
