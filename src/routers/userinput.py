from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.models.models import Cv,TextPrompts
from src.core.security import auth_scheme , get_current_user
from src.services.inputfunc import InputService
router = APIRouter(tags=["User Input"], prefix="/userinput")

@router.post("/upload-cv", status_code=status.HTTP_200_OK)
async def upload_cv(
    cv_data: bytes,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db) # Get database session
): 
    return await InputService.upload_cv(
        token=token,
        db=db,
        cv_data=cv_data
    )


@router.post("/create-prompt", status_code=status.HTTP_200_OK)
async def create_prompt(
    name: str,
    prompt_text: str,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db) # Get database session
):
    return await InputService.create_prompt(
        token=token,
        db=db,
        name=name,
        prompt_text=prompt_text
    )