from pydantic import BaseModel, EmailStr
from datetime import datetime

class BaseConfig: # common config for all schemas
    from_attributes = True

class CvUploadBase(BaseModel):
    user_id: int
    CV_data: bytes
    uploaded_at: datetime #this is optional

    class Config(BaseConfig):
        pass 

class JobPromptBase(BaseModel):
    name: str
    prompt_text: str
    created_at: datetime

    class Config(BaseConfig):
        pass