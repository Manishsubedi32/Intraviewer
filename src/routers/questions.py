from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.core.security import auth_scheme , get_current_user
from src.services.questions import QuestionsService
from src.schemas.auth import QuestionBase

router = APIRouter(tags=["Questions"], prefix ="/questions")

@router.get("/all",status_code=status.HTTP_200_OK)

async def get_questions(token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db) # Get database session
):
    return await QuestionsService.allQuestions(token=token, db= db)

@router.post("/add",status_code=status.HTTP_200_OK)

async def add_question(
    question: QuestionBase,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme), # Extract token from Authorization header
    db: Session = Depends(get_db) # Get database session
    
):
    return await QuestionsService.addQuestion(token=token, db= db, question=question)