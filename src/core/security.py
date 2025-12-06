from fastapi.security.http import HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timedelta
from src.core.config import settings
from jose import JWTError, jwt
from src.schemas.auth import TokenResponse
from fastapi import HTTPException, Depends
from src.models.models import User
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer
from src.db.database import get_db
from src.utils.responses import ResponseHandler
from typing import Union, Any, Optional

# Changed scheme to argon2 to avoid bcrypt 72-byte limit and compatibility issues
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") 
auth_scheme = HTTPBearer()

ALGORITHM = settings.algorithm# the algorithm used for JWT encoding and decoding (it uses HS256 here)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str: # it takes subject (user id) and optional expiry time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta # if expires_delta is given use that
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes) # or else use this
    
    to_encode = {"exp": expire, "sub": str(subject)} #this is the payload of the token
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM) # this encodes the payload with the secret key and algorithm
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Argon2 handles long passwords securely, so we don't need pre-hashing
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # Argon2 handles long passwords securely, so we don't need pre-hashing
    return pwd_context.hash(password)


# Create Access & Refresh Token
async def get_user_token(id: int, refresh_token=None):
    payload = {"id": id}

    access_token_expiry = timedelta(minutes=settings.access_token_expire_minutes)

    access_token = create_access_token(payload, access_token_expiry)

    if not refresh_token:
        refresh_token = create_refresh_token(payload)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_token_expiry.seconds
    )




# Create Refresh Token
def create_refresh_token(data):
    return jwt.encode(data, settings.secret_key, settings.algorithm)


# Get Payload Of Token
def get_token_payload(token):
    try:
        return jwt.decode(token, settings.secret_key, [settings.algorithm])
    except JWTError:
        raise ResponseHandler.invalid_token('access')


def get_current_user(token):
    user = get_token_payload(token.credentials)
    return user.get('id')


def check_admin_role(
        token: HTTPAuthorizationCredentials = Depends(auth_scheme),
        db: Session = Depends(get_db)):
    user = get_token_payload(token.credentials)
    user_id = user.get('id')
    role_user = db.query(User).filter(User.id == user_id).first()
    if role_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")