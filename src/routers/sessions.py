from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.core.security import auth_scheme , get_current_user
from src.services.sessions import SessionService
from fastapi import WebSocket
from src.schemas.session import SessionCreateRequest

router = APIRouter(tags=["Sessions"], prefix="/sessions")

@router.post("/start", status_code=status.HTTP_200_OK)
async def start_session(
    request: SessionCreateRequest,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db), # Get database session
):
    return await SessionService.create_session(
        token=token,
        db=db,
        cv_id=request.cv_id,
        prompt_id=request.prompt_id
    )

@router.post("/end/{session_id}", status_code=status.HTTP_200_OK)
async def end_session(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    return await SessionService.complete_session(
        token=token,
        db=db,
        session_id=session_id
    )

@router.websocket("/ws/sessions/{session_id}")
async def session_websocket_endpoint(websocket: WebSocket, session_id: int,db: Session = Depends(get_db)):
    return await SessionService.handle_session_websocket(websocket=websocket, session_id=session_id, db=db)

@router.get("/questions/{session_id}", status_code=status.HTTP_200_OK)
async def get_session_questions(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db), # Get database session
):
    return await SessionService.fetch_session_questions( # fetch question function to be made soon
        token=token,
        db=db,
        session_id=session_id
    )
#for users to fetch their session analysis and score
@router.get("/{session_id}/analysis")
async def get_session_analysis(
    session_id: int,
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(auth_scheme)
):
    return await SessionService.fetch_session_analysis(
        token=token,
        db=db,
        session_id=session_id
    )

@router.get("/{session_id}/transcript")
async def get_session_transcript(
    session_id: int,
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(auth_scheme)
):
    return await SessionService.fetch_session_transcript(
        token=token,
        db=db,
        session_id=session_id
    )

@router.post("/terminate/{session_id}", status_code=status.HTTP_200_OK)
async def terminate_session(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db), # Get database session
):
    return await SessionService.terminate_session(
        token=token,
        db=db,
        session_id=session_id
    )
@router.delete("/delete/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), 
    db: Session = Depends(get_db), 
):
    return await SessionService.delete_session(
        token=token,
        db=db,
        session_id=session_id
    )