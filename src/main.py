from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.db.database import get_db, test_database_connection, engine, Base

from src.routers import auth, users, questions, application, session, media_stream, transcription
from src.services.transcription import get_transcription_service
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

app = FastAPI(title="Intraviewer Backend", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default dev server
        "http://localhost:3001",  # Alternative port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Import models to ensure they're registered with Base
from src.models.models import (
    User, Questions, Application, InterviewSession, InterviewResponse,
    MediaSession, AudioChunk, VideoFrame
)

@app.on_event("startup")
async def startup_event():
    """Create database tables and load ML models on startup"""
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
    
    # Load faster-whisper model
    try:
        transcription_service = get_transcription_service()
        transcription_service.load_model()
        print("✅ Faster-Whisper model loaded successfully")
    except Exception as e:
        print(f"⚠️  Failed to load transcription model: {e}")
        print("   Transcription features will be unavailable")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of services"""
    try:
        transcription_service = get_transcription_service()
        transcription_service.shutdown()
        print("✅ Transcription service shut down")
    except Exception as e:
        print(f"⚠️  Error during shutdown: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to Intraviewer Backend"}

@app.post("/dev/reset-db")
async def reset_database_endpoint():
    """Development endpoint to reset database"""
    try:
        print("⚠️  Resetting database...")
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables...")
        Base.metadata.create_all(bind=engine)
        print("Created all tables...")
        return {"message": "✅ Database reset complete."}
    except Exception as e:
        return {"error": f"Database reset failed: {str(e)}"}
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/db/create-tables")
async def create_tables():
    """Manually create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        return {"message": "Database tables created successfully"}
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/db/debug")
async def debug_connection():
    """Debug database connection configuration"""
    from src.db.database import DATABASE_URL
    
    return {
        "DATABASE_URL": DATABASE_URL,
        "DB_USERNAME": os.getenv('DB_USERNAME'),
        "DB_PASSWORD": os.getenv('DB_PASSWORD'), 
        "DB_HOST": os.getenv('DB_HOST'),
        "DB_PORT": os.getenv('DB_PORT'),
        "DB_NAME": os.getenv('DB_NAME'),
        "Full_ENV_DATABASE_URL": os.getenv('DATABASE_URL')
    }

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(media_stream.router)
app.include_router(transcription.router)
app.include_router(questions.router)
app.include_router(application.router)
app.include_router(session.router)