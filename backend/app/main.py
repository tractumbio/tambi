from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    ask,
    contracts,
    health,
    metrics,
    monthly_reports,
    opportunities,
    research,
    visualize,
)
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title="Defence Consulting Intelligence Hub API",
    version="0.1.0",
    description="Backend API for the Defence Consulting Intelligence Hub. "
    "Currently a scaffold — see docs/ARCHITECTURE.md for the target design.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(metrics.router, prefix=settings.api_v1_prefix)
app.include_router(contracts.router, prefix=settings.api_v1_prefix)
app.include_router(opportunities.router, prefix=settings.api_v1_prefix)
app.include_router(ask.router, prefix=settings.api_v1_prefix)
app.include_router(research.router, prefix=settings.api_v1_prefix)
app.include_router(monthly_reports.router, prefix=settings.api_v1_prefix)
app.include_router(visualize.router, prefix=settings.api_v1_prefix)
