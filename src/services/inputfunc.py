from typing import Optional
from fastapi import UploadFile, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.models.models import Cv, TextPrompts, InterviewSession, SessionStatus
from src.utils.file_parser import extract_text_from_file
from src.core.security import get_current_user

class InputService:
    
    @staticmethod
    async def _parse_input_to_text(
        cv_file: Optional[UploadFile],
        cv_text: Optional[str],
        job_text: str,
    ) -> tuple[str, str, bytes]:

        
        # ---- 1. Process CV ----
        cv_bytes = None
        cv_extracted = ""

        if cv_file:
            # Read file bytes (works for PDF, Image, etc.)
            cv_bytes = await cv_file.read()
            # Extract text using the utility function
            try:
                cv_extracted = extract_text_from_file(cv_bytes, cv_file.filename)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to parse CV file: {str(e)}")
        elif cv_text:
            cv_extracted = cv_text
            cv_bytes = cv_text.encode('utf-8') # Store text as bytes if no file provided
        else:
            raise HTTPException(status_code=400, detail="CV is required (file or text)")

        #just error handling for job_text
        if not job_text or not job_text.strip():
            raise HTTPException(status_code=400, detail="Job description is required")

        return cv_extracted.strip(), job_text.strip(), cv_bytes

    @staticmethod
    async def process_data(
        db: Session,
        token: HTTPAuthorizationCredentials,
        cv_file: Optional[UploadFile],
        cv_text: Optional[str],
        job_topic: Optional[UploadFile],
        job_text: str,
        background_tasks: BackgroundTasks
    ):
        user_id = get_current_user(token)# requesting user

        
        cv_clean_text, job_clean_text, cv_raw_bytes = await InputService._parse_input_to_text(
            cv_file, cv_text,job_text
        )

        # 2. Save CV
        new_cv = Cv(
            user_id=user_id,
            CV_data=cv_raw_bytes,     # Storing the raw file (PDF/Image bytes)
            cv_text=cv_clean_text     # Storing the extracted text for AI
        )
        db.add(new_cv)
        db.flush() # this is done to get the id of new_cv before commit

        # 3. Save Job Description (Prompt)
        new_prompt = TextPrompts(
            name=f"Job Prompt for User {user_id} about {job_topic}",
            prompt_text=job_clean_text
        )
        db.add(new_prompt)
        db.flush() 
        db.commit()

        db.refresh(new_cv)
        db.refresh(new_prompt)
        

        return {
            "message": "Data stored successfully",
            "cv_id": new_cv.id,
            "prompt_id": new_prompt.id
        }