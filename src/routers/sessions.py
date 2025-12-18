from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.db.database import get_db
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

@router.websocket("/ws/sessions/{session_id}")
async def session_websocket_endpoint(websocket: Websocket, session_id: int,db: Session = Depends(get_db)):
    return await SessionService.handle_session_websocket(websocket=websocket, session_id=session_id, db=db)