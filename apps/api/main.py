from fastapi import FastAPI

from packages.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {"status": "ready", "paper_trading": settings.paper_trading}


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "environment": settings.environment}
