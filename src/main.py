from fastapi import FastAPI
from src.db.database import get_db, test_database_connection, engine, Base
from fastapi.middleware.cors import CORSMiddleware
from src.routers import auth, users, questions, userinput, sessions,tips
from src.models import models # Ensure all models are loaded for create_all
import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, UploadFile, File

# Load environment variables
load_dotenv()

app = FastAPI(title="Intraviewer Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    

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

@app.on_event("startup")

async def create_db_tables():
    """Create database tables on startup"""
    Base.metadata.create_all(bind=engine)
    test_database_connection()
    print("☑️ Database connected and tables created (if not exist).")

@app.get("/")
async def root():
    return {"message": "Welcome to Intraviewer Backend"}
@app.get("/health")
async def health_check():
    return {"status": "OK"}





app.include_router(auth.router) #yesma authentication is covered
app.include_router(users.router) # user related operations like getting user details, and change password
app.include_router(questions.router) # question related operations like adding, updating, deleting questions
app.include_router(userinput.router) # users session detail like uploading cv and text prompts
app.include_router(sessions.router) # interview session related operations like creating session and handling websocket for live audio/video
app.include_router(tips.router) # for fetching random tips for interview