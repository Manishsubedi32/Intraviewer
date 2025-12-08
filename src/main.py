from fastapi import FastAPI
from src.db.database import get_db, test_database_connection, engine, Base

from src.routers import auth, users, questions
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

app = FastAPI(title="Intraviewer Backend", version="1.0.0")
    

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