"""仅验证出生资料，不在程序中计算命理对应关系。"""

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .schemas import Profile


class RomanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    birth_date: date
    birth_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    birth_place: str = Field(min_length=1, max_length=80)
    time_basis: Literal["北京时间 UTC+8"] = "北京时间 UTC+8"
    calendar: Literal["公历"] = "公历"
    relationship_status: Literal["单身", "正在了解", "已有伴侣"] = "单身"
    year: int = Field(ge=1900, le=2100)
    context: str = Field(default="", max_length=1000)
    profile: Profile | None = None

    @field_validator("birth_date")
    @classmethod
    def valid_birth_date(cls, value):
        today = datetime.now(timezone(timedelta(hours=8))).date()
        if not date(1900, 1, 1) <= value <= today:
            raise ValueError("出生日期应在1900年到今天之间")
        return value
