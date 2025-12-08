from fastapi import HTTPException , Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import Questions, User # sqlalchemy models
from src.schemas.auth import QuestionBase #pydantic model
from src.core.security import get_current_user, auth_scheme
from src.core.security import get_password_hash


class QuestionsService:
    @staticmethod
    async def allQuestions(token: HTTPAuthorizationCredentials, db: Session):
        user_id = get_current_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        questions = db.query(Questions).all()
        return questions

    @staticmethod
    async def addQuestion(token: HTTPAuthorizationCredentials, db: Session, question: QuestionBase):
        user_id = get_current_user(token)
        print(user_id)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.role != 'admin':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can add questions")
        new_question = Questions( # we are converting pydantic model to sqlalchemy model
            **question.model_dump()
        )
        db.add(new_question)
        db.commit()
        db.refresh(new_question)
        return {"message": "Question added successfully"}