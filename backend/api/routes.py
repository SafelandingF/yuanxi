from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from ..bootstrap import Services, build_services
from ..core.config import (
    ConfigUpdate,
    config_status,
    save_settings,
    settings_from_update,
)
from ..domain.romance import RomanceRequest
from ..domain.schemas import ChatRequest, DateRequest, Profile
from .streaming import streaming

router = APIRouter(prefix="/api")


def services(request: Request) -> Services:
    current = getattr(request.app.state, "services", None)
    if current is None:
        raise HTTPException(status_code=503, detail="请先完成模型配置")
    return current


@router.get("/health")
async def health(request: Request):
    ctx = getattr(request.app.state, "services", None)
    if ctx is None:
        return {"status": "setup_required", "configured": False}
    return {
        "status": "ok",
        "configured": True,
        "provider": ctx.settings.llm.provider,
        "model": ctx.settings.llm.model,
        "candidate_count": len(ctx.repository.candidates()),
    }


@router.get("/config")
async def get_config(request: Request):
    current = getattr(request.app.state, "services", None)
    if current is None:
        return config_status()
    return {
        "configured": True,
        "provider": current.settings.llm.provider,
        "base_url": current.settings.llm.base_url,
        "model": current.settings.llm.model,
        "has_api_key": True,
    }


@router.put("/config")
async def update_config(body: ConfigUpdate, request: Request):
    async with request.app.state.configuration_lock:
        replacement = None
        try:
            settings = settings_from_update(body)
            replacement = build_services(settings)
            save_settings(settings)
        except RuntimeError as exc:
            if replacement is not None:
                await replacement.aclose()
            raise HTTPException(status_code=422, detail=str(exc)) from None
        except Exception:  # noqa: BLE001 - Do not expose paths or submitted secrets.
            if replacement is not None:
                await replacement.aclose()
            raise HTTPException(
                status_code=500, detail="模型配置暂时无法保存，请稍后重试"
            ) from None
        previous = getattr(request.app.state, "services", None)
        request.app.state.services = replacement
        if previous is not None:
            await previous.aclose()
        return {
            "configured": True,
            "provider": settings.llm.provider,
            "base_url": settings.llm.base_url,
            "model": settings.llm.model,
            "has_api_key": True,
        }


@router.post("/agent/sessions")
async def create_session(body: Profile, ctx: Annotated[Services, Depends(services)]):
    return ctx.sessions.create(body)


@router.get("/agent/sessions/{sid}")
async def get_session(sid: str, ctx: Annotated[Services, Depends(services)]):
    return ctx.sessions.get(sid)


@router.post("/agent/sessions/{sid}/chat")
async def chat(
    sid: str, body: ChatRequest, ctx: Annotated[Services, Depends(services)]
):
    return streaming(ctx.sessions.chat(sid, body))


@router.post("/date/plan")
async def plan(body: DateRequest, ctx: Annotated[Services, Depends(services)]):
    return streaming(ctx.dating.plan(body))


@router.post("/analyze", deprecated=True)
async def analyze(body: Profile, ctx: Annotated[Services, Depends(services)]):
    return streaming(ctx.legacy.analyze(body))


@router.post("/romance/calculate")
def romance(body: RomanceRequest, ctx: Annotated[Services, Depends(services)]):
    return streaming(ctx.romance.run(body))
