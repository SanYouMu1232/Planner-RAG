"""规划智库 Backend — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import init_db
from .routers import (
    health,
    projects,
    documents,
    ingestion,
    search,
    conversations,
    drafts,
    provider_configs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="规划智库 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(provider_configs.router, prefix="/api")
