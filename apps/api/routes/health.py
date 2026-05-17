from fastapi import APIRouter

from apps.api.response_utils import ok_response

router = APIRouter()


@router.get("/health")
def health_check():
    return ok_response(status="ok")
