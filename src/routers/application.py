from fastapi import (
    APIRouter, File, UploadFile, Form, Depends,
    HTTPException, BackgroundTasks, status
)
from typing import Optional
from sqlalchemy.orm import Session
from src.db.database import get_db, SessionLocal

from src.schemas.application import ApplicationCreate, ApplicationResponse
from src.models.models import Application
from src.utils.file_parser import extract_text_from_file
from src.services.application import parse_application_with_llm


router = APIRouter(tags =["application"],prefix="/post")


# -------------------------------
# Helper: file/text → raw strings
# -------------------------------
async def _parse_input_to_text(
    cv_file: Optional[UploadFile],
    cv_text: Optional[str],
    job_file: Optional[UploadFile],
    job_text: Optional[str],
) -> tuple[str, str]:

    # ---- CV ----
    if cv_file:
        contents = await cv_file.read()
        cv_raw = extract_text_from_file(contents, cv_file.filename)
    elif cv_text:
        cv_raw = cv_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CV is required (file or text)"
        )

    # ---- Job Description ----
    if job_file:
        contents = await job_file.read()
        job_raw = extract_text_from_file(contents, job_file.filename)
    elif job_text:
        job_raw = job_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is required (file or text)"
        )

    return cv_raw.strip(), job_raw.strip()


# -------------------------------------------------------
# API: Create application + background LLM parsing job
# -------------------------------------------------------
@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_application(
    background_tasks: BackgroundTasks,
    cv_file: Optional[UploadFile] = File(None),
    cv_text: Optional[str] = Form(None),
    job_file: Optional[UploadFile] = File(None),
    job_text: Optional[str] = Form(None),
    user_id: int = 1,   # TODO: replace with actual auth user
    db: Session = Depends(get_db),
):
    # Step 1: Convert mixed input → raw text
    cv_raw, job_raw = await _parse_input_to_text(
        cv_file, cv_text, job_file, job_text
    )

    # Step 2: Pydantic validation
    validated = ApplicationCreate(
        cv_raw=cv_raw,
        job_description_raw=job_raw
    )

    # Step 3: Save to DB
    db_app = Application(
        user_id=user_id,
        cv_raw=validated.cv_raw,
        job_description_raw=validated.job_description_raw
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)

    # Step 4: Run LLM parsing in background
    # IMPORTANT: Create new DB session inside the task
    #background_tasks.add_task(parse_application_with_llm, db_app.id)

    return db_app
