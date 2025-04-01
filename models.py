from datetime import datetime
from sqlalchemy import Column, String, Date, Enum
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr
from enum import Enum as PyEnum
from db import Base

class GenderEnum(str, PyEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    surname = Column(String(50))
    gender = Column(String(10), nullable=False)
    birthdate = Column(Date)
    address = Column(String(200))
    email = Column(String(100), unique=True, index=True)
    mobile = Column(String(15), unique=True)
    hashed_password = Column(String(300))
    profile_photo = Column(String(200), nullable=True)  # New field for profile photo

# Pydantic Schemas
class UserBase(BaseModel):
    name: str
    surname: str | None = None
    gender: GenderEnum
    birthdate: datetime | None = None
    address: str | None = None
    email: EmailStr
    mobile: str
    profile_photo: str | None = None  # New field for profile photo

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: str | None = None

class UserResponse(UserBase):
    id: str
