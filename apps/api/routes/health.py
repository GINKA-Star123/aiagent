"""Health route placeholder."""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}