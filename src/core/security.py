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
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") # setup password hashing manager
auth_scheme = HTTPBearer() # fastapi dependency to extract token from Authorization header (basically gets token from incoming request headers)

ALGORITHM = settings.algorithm# the algorithm used for JWT encoding and decoding (it uses HS256 here retrieved from settings)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str: # it generates jwt token for general API acess to resources
    if expires_delta:
        expire = datetime.utcnow() + expires_delta # if expires_delta is given use that
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes) # or else use this
    
    to_encode = {"exp": expire, "sub": str(subject)} #this is the payload of the token
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM) # this encodes the payload with the secret key and algorithm
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool: # called when user logs in
    # Argon2 handles long passwords securely, so we don't need pre-hashing
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str: # used when user signs up
    # Argon2 handles long passwords securely, so we don't need pre-hashing
    return pwd_context.hash(password)


# Create Access & Refresh Token
async def get_user_token(id: int, refresh_token=None):# this calls the above acess and refresh token and sends to user when user logs in

    access_token_expiry = timedelta(minutes=settings.access_token_expire_minutes)

    access_token = create_access_token(id, access_token_expiry)

    if not refresh_token:
        payload = {"sub": str(id)} # Use 'sub' here for consistency with the access token
        refresh_token = create_refresh_token(payload)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_token_expiry.seconds
    )




# Create Refresh Token
def create_refresh_token(data): #this comes after creation of acess token,as here long lived token is created to get new acess token later
    return jwt.encode(data, settings.secret_key, settings.algorithm)


# Get Payload Of Token
def get_token_payload(token): #it takes the authentication token from the requesting user and decodes it to get the payload
    try:
        return jwt.decode(token, settings.secret_key, [settings.algorithm]) # if the provided token in invlaid then false
    except JWTError:
        raise ResponseHandler.invalid_token('access')


def get_current_user(token): #it gets the current user from the token provided in the request header
    payload = get_token_payload(token.credentials) # it is calling the above function to get the payload from the token
    print(payload)
    user_id = payload.get('sub')
    if user_id is None:
        user_id = payload.get('id')
    if user_id is None:
        raise ResponseHandler.invalid_token('access')
    return int(user_id)



# working
# user signs up -> password hashed with argon2 -> stored in db (function get_password_hash)
# user logs in -> password verified with argon2 -> if valid generate access and refresh token (function verify_password and get_user_token(it calls create_access_token and create_refresh_token)) -> return tokens to user
# user makes request to protected route with access token in header -> token extracted from header and payload (function get_current_user(it calls get_token_payload)) -> user id retrieved from payload -> use id to get user from db