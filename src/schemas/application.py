from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# Internal model: validated RAW TEXT (after file extraction)
class ApplicationCreate(BaseModel):
    cv_raw: str
    job_description_raw: str

    @field_validator("cv_raw", "job_description_raw")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v.strip()


# API Response model
class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    cv_parsed: Optional[Dict[str, Any]] = None
    job_description_parsed: Optional[Dict[str, Any]] = None
    match_analysis: Optional[Dict[str, Any]] = None
    interview_questions: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True