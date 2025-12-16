from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# Interview Question Schemas
# ============================================

class InterviewQuestion(BaseModel):
    id: str
    question: str
    category: str  # technical, behavioral, experience
    difficulty: str  # easy, medium, hard


# ============================================
# Interview Session Schemas
# ============================================

class SessionStartRequest(BaseModel):
    """Request to start a new interview session"""
    questions: List[InterviewQuestion]
    jobDescription: str
    cvFileName: Optional[str] = None
    applicationId: Optional[int] = None


class SessionStartResponse(BaseModel):
    """Response after starting an interview session"""
    sessionId: int
    jobTitle: Optional[str] = None
    jobDescription: str
    questions: List[Dict[str, Any]]
    status: str = "in-progress"
    startTime: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Full session details"""
    id: int
    user_id: int
    application_id: Optional[int] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    questions: List[Dict[str, Any]]
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# Interview Response Schemas
# ============================================

class AddResponseRequest(BaseModel):
    """Request to add a user's response to a question"""
    sessionId: int
    questionId: str
    answer: Optional[str] = None
    duration: int  # in seconds
    audioUrl: Optional[str] = None
    videoUrl: Optional[str] = None


class AddResponseResponse(BaseModel):
    """Response after adding an interview response"""
    id: int
    session_id: int
    question_id: str
    duration: int
    created_at: datetime

    class Config:
        from_attributes = True


class ResponseDetail(BaseModel):
    """Detailed interview response"""
    id: int
    session_id: int
    question_id: str
    answer: Optional[str] = None
    duration: int
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Complete Interview Schemas
# ============================================

class CompleteInterviewRequest(BaseModel):
    """Request to complete an interview session"""
    sessionId: int


class CompleteInterviewResponse(BaseModel):
    """Response after completing interview"""
    sessionId: int
    status: str
    endTime: datetime
    message: str = "Interview completed successfully"

    class Config:
        from_attributes = True
