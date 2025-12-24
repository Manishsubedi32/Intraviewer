from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.models.models import Cv,TextPrompts
from src.core.security import auth_scheme , get_current_user
from src.services.inputfunc import InputService

router = APIRouter(tags=["User Input"], prefix="/userinput")

@router.post("/data", status_code=status.HTTP_201_CREATED)
async def initialize_data(
    background_tasks: BackgroundTasks, # it is a function of fastapi to run tasks in background after response is sent like processing files cv etc  
    cv_file: Optional[UploadFile] = File(None),
    cv_text: Optional[str] = Form(None),
    job_topic: Optional[str] = Form(None),
    job_text: Optional[str] = Form(None),
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db)
):
    return await InputService.process_data(
        db=db,
        token=token,
        cv_file=cv_file,
        cv_text=cv_text,
        job_topic=job_topic,
        job_text=job_text,
        background_tasks=background_tasks
    )