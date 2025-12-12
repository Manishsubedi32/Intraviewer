from fastapi import HTTPException , Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import Cv, TextPrompts # sqlalchemy models
from src.schemas.userinput import CvUploadBase, JobPromptBase #pydantic model
from src.core.security import get_current_user, auth_scheme
from src.core.security import get_password_hash

class InputService:
    @staticmethod
    async def upload_cv(token: HTTPAuthorizationCredentials, db: Session, cv_data: CvUploadBase):
        user_id = get_current_user(token)
        new_cv = Cv(
            user_id=user_id,
            CV_data=cv_data.CV_data,
            uploaded_at=cv_data.uploaded_at
        )
        db.add(new_cv)
        db.commit()
        db.refresh(new_cv)
        return {"message": "CV uploaded successfully", "cv_id": new_cv.id}

    @staticmethod
    async def create_prompt(token: HTTPAuthorizationCredentials, db: Session, prompt: JobPromptBase):
        user_id = get_current_user(token)
        new_prompt = TextPrompts(
            name=prompt.name,
            prompt_text=prompt.prompt_text,
            created_by=user_id,
            created_at=prompt.created_at
        )
        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)
        return {"message": "Prompt created successfully", "prompt_id": new_prompt.id}