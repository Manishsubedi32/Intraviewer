from fastapi import HTTPException , Depends, status
from sqlalchemy.orm import Session
from src.models.models import User
from src.db.database import get_db
from src.core.security import get_current_user, verify_password, get_user_token, get_token_payload
from src.core.security import get_password_hash
from src.utils.responses import ResponseHandler
from src.schemas.auth import ChangePasswordRequest, Signup, UserLogin


class AuthService:
    @staticmethod
    async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
        user = db.query(User).filter(User.email == user_credentials.email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

        if not verify_password(user_credentials.password, user.password):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

        return await get_user_token(id=user.id)

    @staticmethod
    async def signup(db: Session, user: Signup):
        hashed_password = get_password_hash(user.password)
        user.password = hashed_password
        if db.query(User).filter(User.email == user.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        db_user = User(id=None, **user.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return ResponseHandler.create_success(db_user.email, db_user.id, db_user)

    @staticmethod
    async def get_refresh_token(token, db):
        payload = get_token_payload(token)
        user_id = payload.get('id', None)
        if not user_id:
            raise ResponseHandler.invalid_token('refresh')

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ResponseHandler.invalid_token('refresh')

        return await get_user_token(id=user.id, refresh_token=token)
    
    @staticmethod
    async def ChangePassword(db: Session, change_request: ChangePasswordRequest, token):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(change_request.old_password, user.password):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Old password is incorrect")
        new_password = change_request.new_password
        new_password_confirm = change_request.new_password_confirm
        if new_password != new_password_confirm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password and confirmation do not match")
        hashed_password = get_password_hash(new_password)
        user.password = hashed_password
        db.commit()
        return {"message": "Password updated successfully"}