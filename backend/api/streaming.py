import asyncio
import json

from fastapi.responses import StreamingResponse

from ..domain.errors import ModelError
from ..domain.events import event


def encode(item: dict) -> str:
    return "data: " + json.dumps(item, ensure_ascii=False) + "\n\n"


def streaming(generator):
    async def guarded():
        try:
            async for item in generator:
                yield encode(item)
        except asyncio.CancelledError:
            raise
        except ModelError as exc:
            yield encode(event("error", message=str(exc)))
        except Exception:  # noqa: BLE001 - Never expose provider bodies or secrets.
            yield encode(event("error", message="分析暂时失败，请重试。"))
        finally:
            await generator.aclose()

    return StreamingResponse(
        guarded(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
