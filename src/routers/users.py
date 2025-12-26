from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.db.database import get_db
from src.schemas.auth import UserResponse, ChangePasswordRequest
from src.models.models import User
from src.core.security import auth_scheme , get_current_user
from src.services.userdel import UserDeletionService

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

@router.post("/me/password", status_code=status.HTTP_200_OK)

async def change_password(
    change_request: ChangePasswordRequest, # Request body containing old and new passwords and confirmation
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    await AuthService.ChangePassword(
        db=db,
        change_request=change_request,
        token=token
    )
    return {"message": "Password changed successfully"}

@router.delete("delete/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user_account(
    user_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    await UserDeletionService.DeleteAccount(
        User_id=user_id,
        db=db,
        token=token
    )
    return {"message": "User account deleted successfully"}


@router.get("/all", status_code=status.HTTP_200_OK, response_model=list[UserResponse])
async def get_all_users(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    requesting_user_id = get_current_user(token)
    requesting_user = db.query(User).filter(User.id == requesting_user_id).first()
    if requesting_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can access all users")
    
    users = db.query(User).all()
    return users