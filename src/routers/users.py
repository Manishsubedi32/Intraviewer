from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.db.database import get_db
from src.schemas.auth import UserResponse
from src.models.models import User
from src.core.security import auth_scheme , get_current_user

router = APIRouter(tags=["Users"], prefix="/users")

@router.get("/me",status_code=status.HTTP_200_OK, response_model=UserResponse)

async def get_user_details(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db) # Get database session
   
):
    user_id = get_current_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    print(user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
