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


@router.post("/generate/{session_id}", status_code=status.HTTP_201_CREATED)
async def generate_questions(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    """Generate interview questions with AI-recommended answers for a session."""
    questions = await QuestionsService.generate_and_save_questions(db, session_id)
    return {
        "message": "Questions generated successfully with recommended answers",
        "session_id": session_id,
        "total_questions": len(questions),
        "questions": questions
    }

@router.get("/session/{session_id}", status_code=status.HTTP_200_OK)
async def get_session_questions(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    """Get all questions for a session (without auth - for interview display)."""
    questions = await QuestionsService.get_questions_by_session(db, session_id)
    return questions

@router.get("/session/{session_id}/with-answers", status_code=status.HTTP_200_OK)
async def get_questions_with_answers(
    session_id: int,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    """Get questions with recommended answers (requires auth)."""
    return await QuestionsService.get_questions_with_answers(token, db, session_id)