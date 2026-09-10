"""FastAPI 应用入口；业务逻辑位于 services / agents / domain。"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.routes import router
from .bootstrap import build_services
from .core.config import Settings, load_settings
from .domain.errors import Conflict, DomainError, InvalidInput, NotFound
from .domain.ports import LanguageModel, Repository


def create_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
    model: LanguageModel | None = None,
) -> FastAPI:
    if settings is None and (repository is not None or model is not None):
        raise ValueError("注入测试依赖时需要显式提供 Settings")

    @asynccontextmanager
    async def lifespan(app):
        if not hasattr(app.state, "services"):
            try:
                app.state.services = build_services(load_settings())
            except RuntimeError:
                # Keep the local server alive so the browser can show first-run setup.
                app.state.services = None
        try:
            yield
        finally:
            if app.state.services is not None:
                await app.state.services.aclose()

    app = FastAPI(title="缘析本地服务", lifespan=lifespan)
    app.state.configuration_lock = asyncio.Lock()
    # Explicit injection supports tests without YAML, API keys or production databases.
    if settings is not None:
        app.state.services = build_services(settings, repository, model)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            status_code=422,
            content={"detail": "输入不符合要求，请检查年龄、兴趣、预算与开始时间。"},
        )

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        status = {NotFound: 404, Conflict: 409, InvalidInput: 422}.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    app.include_router(router)
    return app


app = create_app()
