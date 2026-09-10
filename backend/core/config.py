from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORT = 8000
DEFAULT_PROVIDER = "volcengine-ark"
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed-2-0-pro-260215"


class ModelConfig(BaseModel):
    provider: str = DEFAULT_PROVIDER
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: SecretStr
    timeout_seconds: int = Field(default=90, ge=10, le=300)
    temperature: float = Field(default=0.4, ge=0, le=1)
    max_tokens: int = Field(default=2500, ge=128, le=8192)
    thinking: str = "disabled"


class Settings(BaseModel):
    port: int = DEFAULT_PORT
    database_path: Path = ROOT / "data/yuanxi.db"
    llm: ModelConfig


class ConfigUpdate(BaseModel):
    """Values accepted from the local first-run configuration dialog."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    api_key: str = Field(default="", max_length=2000)
    provider: str = Field(min_length=1, max_length=50)
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=200)


def _read_raw() -> dict:
    path = ROOT / "config.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return data


def _settings_from_raw(raw: dict) -> Settings:
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
    if llm.get("provider", DEFAULT_PROVIDER) != DEFAULT_PROVIDER and (
        not llm.get("base_url") or not llm.get("model")
    ):
        raise ValueError("base_url and model are required")
    model = ModelConfig.model_validate(llm)
    url = urlparse(model.base_url)
    if (
        url.scheme not in ("https", "http")
        or not url.hostname
        or url.query
        or url.fragment
        or url.username
        or url.password
        or url.path.rstrip("/").endswith("/chat/completions")
    ):
        raise ValueError("invalid endpoint")
    if model.thinking not in ("disabled", "enabled"):
        raise ValueError("invalid thinking")
    app = raw.get("app") or {}
    db = Path(app.get("database_path", "./data/yuanxi.db"))
    return Settings(
        port=int(app.get("port", DEFAULT_PORT)),
        database_path=db if db.is_absolute() else ROOT / db,
        llm=model,
    )


def load_settings() -> Settings:
    try:
        return _settings_from_raw(_read_raw())
    except Exception:  # noqa: BLE001 - Do not expose secrets or model payloads.
        raise RuntimeError(
            "config.yaml 配置无效，请检查 apikey、llm.base_url 和 llm.model"
        ) from None


def load_port() -> int:
    """Read only the local HTTP port, even while model setup is incomplete."""

    try:
        port = int((_read_raw().get("app") or {}).get("port", DEFAULT_PORT))
        return port if 1 <= port <= 65535 else DEFAULT_PORT
    except Exception:  # noqa: BLE001 - Startup must reach the setup dialog.
        return DEFAULT_PORT


def config_status() -> dict:
    """Return safe display values. The secret is deliberately never returned."""

    try:
        settings = load_settings()
        return {
            "configured": True,
            "provider": settings.llm.provider,
            "base_url": settings.llm.base_url,
            "model": settings.llm.model,
            "has_api_key": True,
        }
    except RuntimeError:
        try:
            raw = _read_raw()
            llm = raw.get("llm") or {}
            provider = str(llm.get("provider") or DEFAULT_PROVIDER)
            base_url = str(
                llm.get("base_url")
                or (DEFAULT_BASE_URL if provider == DEFAULT_PROVIDER else "")
            )
            model = str(
                llm.get("model")
                or (DEFAULT_MODEL if provider == DEFAULT_PROVIDER else "")
            )
            raw_key = (
                raw.get("apikey")
                or raw.get("api_key")
                or llm.get("api_key")
                or llm.get("apikey")
            )
            has_api_key = bool(
                isinstance(raw_key, str)
                and raw_key.strip()
                and not raw_key.startswith("YOUR_")
            )
        except Exception:  # noqa: BLE001 - Malformed config is repaired by the dialog.
            provider, base_url, model = (
                DEFAULT_PROVIDER,
                DEFAULT_BASE_URL,
                DEFAULT_MODEL,
            )
            has_api_key = False
        return {
            "configured": False,
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "has_api_key": has_api_key,
        }


def settings_from_update(update: ConfigUpdate) -> Settings:
    """Validate a dialog submission while allowing an existing key to be retained."""

    try:
        raw = _read_raw()
        old_llm = raw.get("llm") or {}
        old_key = (
            raw.get("apikey")
            or raw.get("api_key")
            or old_llm.get("api_key")
            or old_llm.get("apikey")
            or ""
        )
        key = update.api_key or old_key
        candidate = {
            **raw,
            "apikey": key,
            "llm": {
                **old_llm,
                "provider": update.provider,
                "base_url": update.base_url,
                "model": update.model,
            },
        }
        return _settings_from_raw(candidate)
    except Exception:  # noqa: BLE001 - Do not echo submitted credentials.
        raise RuntimeError(
            "模型配置无效，请检查 API Key、API 地址和模型名称"
        ) from None


def save_settings(settings: Settings) -> None:
    """Atomically persist validated local settings without exposing the key."""

    try:
        raw = _read_raw()
    except Exception:  # noqa: BLE001 - A valid submission may repair a broken file.
        raw = {}
    app = dict(raw.get("app") or {})
    app.setdefault("port", settings.port)
    app.setdefault("database_path", "./data/yuanxi.db")
    llm = settings.llm
    saved = {
        "apikey": llm.api_key.get_secret_value(),
        "app": app,
        "llm": {
            "provider": llm.provider,
            "base_url": llm.base_url,
            "model": llm.model,
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens,
            "timeout_seconds": llm.timeout_seconds,
            **({"thinking": llm.thinking} if llm.provider == DEFAULT_PROVIDER else {}),
        },
    }
    path = ROOT / "config.yaml"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        yaml.safe_dump(saved, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    temporary.replace(path)
