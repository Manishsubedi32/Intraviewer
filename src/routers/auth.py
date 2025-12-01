from fastapi import APIRouter, Depends, status, Header
from sqlalchemy.orm import Session #this is the data structure that helps us to interact with the database
from app.sevices.auth import AuthService
from app.db.database import get_db
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from app.schemas.auth import UserOut, Signup
