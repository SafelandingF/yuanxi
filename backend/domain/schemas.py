from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=12)
    age: int = Field(ge=18, le=80)
    city: str = Field(min_length=1, max_length=30)
    goal: Literal["认真长久", "慢慢了解", "先交朋友"]
    rhythm: Literal["规律慢生活", "自由随性", "忙碌但充实"]
    interests: list[str] = Field(min_length=1, max_length=10)
    companionship: Literal["每周 2–3 次", "每周 1 次", "每月 1–2 次"]
    note: str = Field(default="", max_length=300)

    @field_validator("interests")
    @classmethod
    def interests_valid(cls, values):
        if any(
            v
            not in {
                "咖啡",
                "电影",
                "散步",
                "摄影",
                "阅读",
                "旅行",
                "音乐",
                "运动",
                "看展",
                "游戏",
            }
            for v in values
        ):
            raise ValueError("请选择提供的兴趣标签")
        return list(dict.fromkeys(values))


class DateRequest(BaseModel):
    meal_preference: Literal["都可以", "想吃锅类", "偏爱简餐", "偏爱素食"] = "都可以"
    spending_style: Literal["性价比优先", "均衡安排", "体验优先"] = "均衡安排"
    food_restrictions: list[Literal["不吃辣", "素食"]] = Field(
        default_factory=list, max_length=2
    )
    avoid_ids: list[str] = Field(default_factory=list, max_length=6)
    session_id: str = Field(min_length=1, max_length=50)
    candidate_id: int = Field(ge=1)
    budget: int = Field(ge=30, le=500)
    start: str = Field(pattern=r"^(1[0-9]|20):[0-5][0-9]$")

    @field_validator("start")
    @classmethod
    def check_time(cls, value):
        if value > "20:00":
            raise ValueError("请在 10:00 到 20:00 之间开始")
        return value

    @field_validator("avoid_ids")
    @classmethod
    def valid_avoid_ids(cls, values):
        if any(not value or len(value) > 50 for value in values):
            raise ValueError("需要避开的项目 ID 无效")
        return list(dict.fromkeys(values))


class PortraitResult(BaseModel):
    relationship_type: str = Field(max_length=50)
    summary: str = Field(max_length=500)
    core_preferences: list[str] = Field(min_length=1, max_length=6)
    possible_conflicts: list[str] = Field(max_length=5)


class MatchDetail(BaseModel):
    id: int
    strengths: list[str] = Field(min_length=1, max_length=4)
    conflicts: list[str] = Field(max_length=4)
    explanation: str = Field(max_length=500)


class MatchResult(BaseModel):
    candidates: list[MatchDetail] = Field(min_length=3, max_length=3)


class DateChoice(BaseModel):
    meal_id: str
    activity_id: str
    drink_id: str
    reason: str = Field(min_length=1, max_length=500)
    conflict_detected: bool
    conflict_description: str = Field(max_length=500)


class FeedbackResult(BaseModel):
    explanation: str = Field(min_length=1, max_length=500)


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    city: str | None = Field(default=None, min_length=1, max_length=30)
    age_min: int | None = Field(default=None, ge=18, le=80)
    age_max: int | None = Field(default=None, ge=18, le=80)
    interests: list[
        Literal[
            "咖啡",
            "电影",
            "散步",
            "摄影",
            "阅读",
            "旅行",
            "音乐",
            "运动",
            "看展",
            "游戏",
        ]
    ] = Field(default_factory=list, max_length=10)
    companionship: Literal["每周 2–3 次", "每周 1 次", "每月 1–2 次"] | None = None
    goal: Literal["认真长久", "慢慢了解", "先交朋友"] | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.age_min and self.age_max and self.age_min > self.age_max:
            raise ValueError("年龄下限不能超过上限")
        return self


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: int = Field(ge=1)
    revision: int = Field(ge=0)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: str = Field(min_length=1, max_length=64)
    text: str = Field(default="", max_length=2000)
    selection: Selection | None = None

    @model_validator(mode="after")
    def content_required(self):
        if not self.text and self.selection is None:
            raise ValueError("请输入消息")
        return self
