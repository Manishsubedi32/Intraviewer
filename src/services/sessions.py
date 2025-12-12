from fastapi import HTTPException , Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import SessionStatus, InterviewSession, User # sqlalchemy models
from src.schemas.session import SessionBase #pydantic model
from src.core.security import get_current_user, auth_scheme
from src.core.security import get_password_hash

class SessionService:
    @staticmethod
    async def create_session(token: HTTPAuthorizationCredentials, db: Session):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        new_session = InterviewSession(
            user_id=user_id,
            status=SessionStatus.ONGOING
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"message": "Session created successfully", "session_id": new_session.id}