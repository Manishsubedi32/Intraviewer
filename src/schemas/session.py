from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List

class BaseConfig: # common config for all schemas
    from_attributes = True

class SessionBase(BaseModel): # this is the serializer for InterviewSession model
    user_id: int
    status: str
    start_time: datetime
    final_score: int | None = None
    analysis: str | None = None

    class Config(BaseConfig):
        pass

class SessionCreateRequest(BaseModel):
    cv_id: int
    prompt_id: int
