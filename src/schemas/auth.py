from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List

class BaseConfig:
    from_attributes = True


# class UserBase(BaseModel): # youshould never expose password in UserBase bedcause it is used in UserOut
#     id: int
#     email: EmailStr
#     password: str
#     role: str
#     is_active: bool
#     created_at: datetime

#     class Config(BaseConfig):
#         pass

#Base schema for shared properties
class UserSchemaBase(BaseModel):
    username: str

    class Config(BaseConfig):
        pass

class Signup(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str

    class Config(BaseConfig):
        pass

#Schema for Response for api - does not include password
class UserResponse(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: str
    is_active: bool
    created_at: datetime

    class Config(BaseConfig):
        pass



class UserOut(BaseModel):
    message: str
    data: UserResponse

    class Config(BaseConfig):
        pass

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Token
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'
    expires_in: int