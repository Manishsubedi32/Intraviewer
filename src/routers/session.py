from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from src.db.database import get_db
from src.models.models import InterviewSession, InterviewResponse, Application
from src.schemas.session import (
    SessionStartRequest,
    SessionStartResponse,
    SessionResponse,
    AddResponseRequest,
    AddResponseResponse,
    ResponseDetail,
    CompleteInterviewRequest,
    CompleteInterviewResponse
)


router = APIRouter(tags=["session"], prefix="/sessions")


# ============================================
# Start Interview Session
# ============================================

@router.post(
    "/start",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED
)
async def start_interview_session(
    request: SessionStartRequest,
    user_id: int = 1,  # TODO: Replace with actual auth user from JWT
    db: Session = Depends(get_db)
):
    """
    Start a new interview session
    
    Creates a new interview session record with the provided questions
    and job description. Links to application if applicationId provided.
    """
    
    # Validate application_id exists if provided
    if request.applicationId:
        application = db.query(Application).filter(
            Application.id == request.applicationId
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID {request.applicationId} not found"
            )
    
    # Convert Pydantic questions to dict for JSONB storage
    questions_dict = [q.model_dump() for q in request.questions]
    
    # Create new session
    new_session = InterviewSession(
        user_id=user_id,
        application_id=request.applicationId,
        job_title=None,  # Can be extracted from job description if needed
        job_description=request.jobDescription,
        questions=questions_dict,
        status="in-progress"
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return SessionStartResponse(
        sessionId=new_session.id,
        jobTitle=new_session.job_title,
        jobDescription=new_session.job_description,
        questions=new_session.questions,
        status=new_session.status,
        startTime=new_session.start_time
    )


# ============================================
# Get Session Details
# ============================================

@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK
)
async def get_session(
    session_id: int,
    user_id: int = 1,  # TODO: Replace with actual auth user
    db: Session = Depends(get_db)
):
    """
    Get details of a specific interview session
    """
    
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return session


# ============================================
# Get All User Sessions
# ============================================

@router.get(
    "/",
    response_model=List[SessionResponse],
    status_code=status.HTTP_200_OK
)
async def get_user_sessions(
    user_id: int = 1,  # TODO: Replace with actual auth user
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all interview sessions for the current user
    """
    
    sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    return sessions


# ============================================
# Add Response to Session
# ============================================

@router.post(
    "/responses",
    response_model=AddResponseResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_interview_response(
    request: AddResponseRequest,
    user_id: int = 1,  # TODO: Replace with actual auth user
    db: Session = Depends(get_db)
):
    """
    Add a user's response to a question in an interview session
    
    Stores the answer text, duration, and optionally audio/video URLs.
    Can be called in real-time as user answers each question.
    """
    
    # Verify session exists and belongs to user
    session = db.query(InterviewSession).filter(
        InterviewSession.id == request.sessionId,
        InterviewSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.sessionId} not found"
        )
    
    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add responses to a completed session"
        )
    
    # Create response record
    new_response = InterviewResponse(
        session_id=request.sessionId,
        question_id=request.questionId,
        answer=request.answer,
        duration=request.duration,
        audio_url=request.audioUrl,
        video_url=request.videoUrl
    )
    
    db.add(new_response)
    db.commit()
    db.refresh(new_response)
    
    return new_response


# ============================================
# Get Session Responses
# ============================================

@router.get(
    "/{session_id}/responses",
    response_model=List[ResponseDetail],
    status_code=status.HTTP_200_OK
)
async def get_session_responses(
    session_id: int,
    user_id: int = 1,  # TODO: Replace with actual auth user
    db: Session = Depends(get_db)
):
    """
    Get all responses for a specific session
    """
    
    # Verify session exists and belongs to user
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    responses = db.query(InterviewResponse).filter(
        InterviewResponse.session_id == session_id
    ).all()
    
    return responses


# ============================================
# Complete Interview Session
# ============================================

@router.post(
    "/complete",
    response_model=CompleteInterviewResponse,
    status_code=status.HTTP_200_OK
)
async def complete_interview_session(
    request: CompleteInterviewRequest,
    user_id: int = 1,  # TODO: Replace with actual auth user
    db: Session = Depends(get_db)
):
    """
    Mark an interview session as completed
    
    Updates the session status to 'completed' and sets the end time.
    This can trigger additional analysis pipelines.
    """
    
    # Verify session exists and belongs to user
    session = db.query(InterviewSession).filter(
        InterviewSession.id == request.sessionId,
        InterviewSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.sessionId} not found"
        )
    
    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already completed"
        )
    
    # Update session
    session.status = "completed"
    session.end_time = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    
    # TODO: Trigger analysis pipeline here
    # - Analyze responses
    # - Generate feedback
    # - Calculate scores
    
    return CompleteInterviewResponse(
        sessionId=session.id,
        status=session.status,
        endTime=session.end_time
    )


# ============================================
# Delete Session (Optional)
# ============================================

@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_session(
    session_id: int,
    user_id: int = 1,  # TODO: Replace with actual auth user
    db: Session = Depends(get_db)
):
    """
    Delete an interview session and all its responses
    """
    
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Delete all responses first
    db.query(InterviewResponse).filter(
        InterviewResponse.session_id == session_id
    ).delete()
    
    # Delete session
    db.delete(session)
    db.commit()
    
    return None
