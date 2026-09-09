"""依赖契约：业务与 Agent 只面向能力，不依赖 HTTPX / SQLite 实现。"""

from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

Result = TypeVar("Result", bound=BaseModel)


class Repository(Protocol):
    def candidates(self) -> list[dict[str, Any]]: ...
    def get(self, key: str) -> dict[str, Any] | None: ...
    def save(self, key: str, value: dict[str, Any]) -> None: ...


class LanguageModel(Protocol):
    async def structured(
        self,
        system: str,
        data: Any,
        schema: type[Result],
        validate: Callable[[Result], None] | None = None,
    ) -> Result: ...
    def stream(self, system: str, data: Any) -> AsyncIterator[str]: ...
    def agent_step(
        self, messages: list[dict], tools: list[dict]
    ) -> AsyncIterator[dict]: ...
    async def aclose(self) -> None: ...
