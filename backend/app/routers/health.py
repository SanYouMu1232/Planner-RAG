"""Health check endpoint."""

from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(ok=True, message="规划智库后端运行中")
