from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from apis.database.database import get_db, test_database_connection, engine, Base
from apis.database.model import HealthCheck, User
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Intraviewer Backend", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/db/test")
async def test_db_connection():
    """Test basic database connectivity"""
    is_connected, message = test_database_connection()
    if not is_connected:
        raise HTTPException(status_code=500, detail=message)
    
    return {
        "status": "success",
        "message": message,
        "database_url": os.getenv("DATABASE_URL", "Not configured")
    }

@app.get("/db/info")
async def get_db_info():
    """Get database information"""
    try:
        with engine.connect() as connection:
            # Get database version
            version_result = connection.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get current database name
            db_name_result = connection.execute(text("SELECT current_database()"))
            db_name = db_name_result.scalar()
            
            # Get current user
            user_result = connection.execute(text("SELECT current_user"))
            user = user_result.scalar()
            
            return {
                "database_version": version,
                "database_name": db_name,
                "current_user": user,
                "connection_status": "active"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database info query failed: {str(e)}")

@app.post("/db/create-tables")
async def create_database_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        return {"message": "Database tables created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create tables: {str(e)}")

@app.get("/db/tables")
async def list_tables():
    """List all tables in the database"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")

@app.post("/db/test-insert")
async def test_database_insert(db: Session = Depends(get_db)):
    """Test inserting data into database"""
    try:
        # Create a test health check entry
        health_entry = HealthCheck(
            status="test",
            message="Database insert test successful"
        )
        db.add(health_entry)
        db.commit()
        db.refresh(health_entry)
        
        return {
            "message": "Database insert test successful",
            "entry_id": health_entry.id,
            "timestamp": health_entry.timestamp
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database insert failed: {str(e)}")

@app.get("/db/test-read")
async def test_database_read(db: Session = Depends(get_db)):
    """Test reading data from database"""
    try:
        # Read the latest health check entries
        health_entries = db.query(HealthCheck).order_by(HealthCheck.timestamp.desc()).limit(5).all()
        
        return {
            "message": "Database read test successful",
            "entries_count": len(health_entries),
            "latest_entries": [
                {
                    "id": entry.id,
                    "status": entry.status,
                    "message": entry.message,
                    "timestamp": entry.timestamp
                }
                for entry in health_entries
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database read failed: {str(e)}")
    

@app.get("/db/debug")
async def debug_connection():
    """Debug database connection configuration"""
    from apis.database.database import DATABASE_URL
    
    return {
        "DATABASE_URL": DATABASE_URL,
        "DB_USERNAME": os.getenv('DB_USERNAME'),
        "DB_PASSWORD": os.getenv('DB_PASSWORD'), 
        "DB_HOST": os.getenv('DB_HOST'),
        "DB_PORT": os.getenv('DB_PORT'),
        "DB_NAME": os.getenv('DB_NAME'),
        "Full_ENV_DATABASE_URL": os.getenv('DATABASE_URL')
    }