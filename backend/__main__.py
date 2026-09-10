import uvicorn

from .core.config import load_port

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", host="127.0.0.1", port=load_port(), access_log=False
    )
