from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ..bootstrap import Services
from ..domain.schemas import ChatRequest, DateRequest, Profile
from .streaming import streaming

router = APIRouter(prefix="/api")


def services(request: Request) -> Services:
    return request.app.state.services


@router.get("/health")
async def health(ctx: Annotated[Services, Depends(services)]):
    return {
        "status": "ok",
        "provider": "volcengine-ark",
        "model": ctx.settings.llm.model,
        "candidate_count": len(ctx.repository.candidates()),
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
