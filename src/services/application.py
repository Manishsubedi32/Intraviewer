from sqlalchemy.orm import Session
from src.models.models import Application
from src.utils.llm_client import parse_with_phi3
from src.db.database import SessionLocal


async def parse_application_with_llm(app_id: int) -> None:
    """Background task to parse CV + job description and update DB."""
    # Create a new database session for the background task
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app:
            return

        try:
            cv_parsed = await parse_with_phi3(app.cv_raw, "cv")
            job_parsed = await parse_with_phi3(app.job_description_raw, "job")

            app.cv_parsed = cv_parsed
            app.job_description_parsed = job_parsed
            db.commit()
        except Exception as e:
            # Log error (in prod, use logging or Sentry)
            print(f"LLM parsing failed for app {app_id}: {str(e)}")
            db.rollback()
    finally:
        db.close()