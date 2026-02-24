from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from src.core.security import auth_scheme
from src.services.tipsforInterview import TipsForInterviewService

router = APIRouter(tags=["Tips"], prefix="/tips")

@router.get("/random", status_code=status.HTTP_200_OK)
async def get_random_tip(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme)
):
    return TipsForInterviewService.get_random_tips(token)
