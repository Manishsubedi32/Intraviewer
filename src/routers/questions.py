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
async def generate_session_questions(
    session_id: int,
   db: Session = Depends(get_db),
   token: HTTPAuthorizationCredentials = Depends(auth_scheme)
):
    """
    Triggers AI to generate questions for a specific session and saves them.
    """
    questions = await QuestionsService.generate_and_save_questions(
        db=db,
        session_id=session_id,
    )
    
    return {
        "message": "Questions generated successfully",
        "count": len(questions),
        "questions": questions
    }

@router.get("/session/{session_id}", status_code=status.HTTP_200_OK)
async def get_questions_with_answers(
    session_id: int,
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(auth_scheme)
):
    """
    Fetches all questions along with their recommended answers for a given session.
    """
    questions = await QuestionsService.get_questions_by_session(db=db, session_id=session_id)
    if not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questions found for this session")
    
    return questions
