import uvicorn

from .core.config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(
        "backend.main:app", host="127.0.0.1", port=settings.port, access_log=False
    )
