from fastapi import HTTPException , Depends, status
from sqlalchemy.orm import Session
from src.models.models import User
from src.db.database import get_db
from src.core.security import get_current_user, verify_password, get_user_token, get_token_payload
from src.core.security import get_password_hash
from src.utils.responses import ResponseHandler
from src.schemas.auth import ChangePasswordRequest, Signup, UserLogin


class UserDeletionService:
    @staticmethod
    async def DeleteAccount(db: Session, token, User_id: int):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if user.role != "admin" and user.id != User_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to delete this account, Only admins can delet the account")
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        user_to_delete = db.query(User).filter(User.id == User_id).first()
        if not user_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to delete not found")
        
        db.delete(user_to_delete)
        db.commit()
        
        return ResponseHandler.create_success("User account deleted successfully", user_id, None)