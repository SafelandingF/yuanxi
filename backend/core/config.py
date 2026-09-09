from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, SecretStr

ROOT = Path(__file__).resolve().parents[2]


class ModelConfig(BaseModel):
    provider: str = "volcengine-ark"
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    model: str = "doubao-seed-2-0-pro-260215"
    api_key: SecretStr
    timeout_seconds: int = Field(default=90, ge=10, le=300)
    temperature: float = Field(default=0.4, ge=0, le=1)
    max_tokens: int = Field(default=2500, ge=128, le=8192)
    thinking: str = "disabled"


class Settings(BaseModel):
    port: int = 8000
    database_path: Path = ROOT / "data/yuanxi.db"
    llm: ModelConfig


def load_settings() -> Settings:
    path = ROOT / "config.yaml"
    if not path.exists():
        raise RuntimeError("请复制 config.template.yaml 为 config.yaml 并填写 apikey")
    try:
        raw = yaml.safe_load(path.read_text()) or {}
        llm = dict(raw.get("llm") or {})
        key = (
            raw.get("apikey")
            or raw.get("api_key")
            or llm.get("api_key")
            or llm.get("apikey")
        )
        if not isinstance(key, str) or not key.strip() or key.startswith("YOUR_"):
            raise ValueError("missing key")
        llm["api_key"] = key.strip()
        model = ModelConfig.model_validate(llm)
        url = urlparse(model.base_url)
        if (
            url.scheme != "https"
            or url.hostname != "ark.cn-beijing.volces.com"
            or url.path.rstrip("/") != "/api/v3"
            or url.query
            or url.fragment
            or url.username
            or url.port not in (None, 443)
        ):
            raise ValueError("invalid endpoint")
        if model.thinking not in ("disabled", "enabled"):
            raise ValueError("invalid thinking")
        app = raw.get("app") or {}
        db = Path(app.get("database_path", "./data/yuanxi.db"))
        return Settings(
            port=int(app.get("port", 8000)),
            database_path=db if db.is_absolute() else ROOT / db,
            llm=model,
        )
    except Exception:  # noqa: BLE001 - Do not expose secrets or model payloads.
        raise RuntimeError(
            "config.yaml 配置无效，请检查 apikey 和方舟模型配置"
        ) from None
