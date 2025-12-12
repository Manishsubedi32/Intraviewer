from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List

class BaseConfig: # common config for all schemas
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
    email: EmailStr
    role: str

    class Config(BaseConfig):
        pass

class Signup(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str
    role: str = "user"

    class Config(BaseConfig):
        pass

#Schema for Response for api - does not include password
class UserResponse(UserSchemaBase):
    id: int
    firstname: str
    lastname: str
    is_active: bool
    role: str = "user"
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

class ChangePasswordRequest(BaseModel): #serializer for changing password
    email: EmailStr
    old_password: str
    new_password: str
    new_password_confirm: str

    class Config(BaseConfig):
        pass

class QuestionBase(BaseModel):
    question_text: str
    answer_text: str
    difficulty_level: str
    topic: str

    class Config(BaseConfig):
        pass
