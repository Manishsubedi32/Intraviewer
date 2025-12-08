from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.db.database import get_db, test_database_connection, engine, Base

from src.routers import auth, users, questions
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
from src.models.models import User

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

@app.get("/")
async def root():
    return {"message": "Welcome to Intraviewer Backend"}

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
app.include_router(questions.router)