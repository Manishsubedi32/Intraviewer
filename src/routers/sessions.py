from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.db.database import get_db
from src.models.models import InterviewSession, User
from src.core.security import auth_scheme , get_current_user
from src.services.sessions import SessionService

router = APIRouter(tags=["Sessions"], prefix="/sessions")

@router.post("/start", status_code=status.HTTP_200_OK)
async def start_session(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db) # Get database session
):
    return await SessionService.create_session(
        token=token,
        db=db
    )