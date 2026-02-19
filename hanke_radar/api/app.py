"""FastAPI application for HankeRadar REST API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hanke_radar.api.routes import router
from hanke_radar.config import settings

app = FastAPI(
    title="HankeRadar API",
    description="Estonian public procurement data for tradespeople",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hanke-radar"}
