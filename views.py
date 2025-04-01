from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
import uuid
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta

from db import get_db
from models import DBUser, UserCreate, UserUpdate, UserResponse

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key"  # Change this to a secure secret key in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expiration time in minutes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user: UserCreate):
        try:
            user_dict = user.dict(exclude={'password'})
            db_user = DBUser(
                id=str(uuid.uuid4()),
                hashed_password=pwd_context.hash(user.password),
                **user_dict
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except Exception as e:
            self.db.rollback()
            print(f"Error creating user: {str(e)}")  # For debugging
            raise HTTPException(
                status_code=400,
                detail=f"Could not create user: {str(e)}"
            )
    
    def get_user(self, user_id: str):
        return self.db.query(DBUser).filter(DBUser.id == user_id).first()
    
    def get_user_all(self):
        return self.db.query(DBUser).all()
    
    def update_user(self, user_id: str, user_data: UserUpdate):
        db_user = self.get_user(user_id)
        if not db_user:
            return None
        
        for key, value in user_data.dict().items():
            if key == 'password' and value:
                db_user.hashed_password = pwd_context.hash(value)
            elif value and key != 'password':
                setattr(db_user, key, value)

        self.db.commit()
        return db_user
    
    def delete_user(self, user_id: str):
        db_user = self.get_user(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        return True

    def authenticate_user(self, email: str, password: str):
        user = self.db.query(DBUser).filter(DBUser.email == email).first()
        if not user or not pwd_context.verify(password, user.hashed_password):
            return False
        return user

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(DBUser).filter(DBUser.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)
    created_user = service.create_user(user)
    return created_user

@router.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)   
    user_data = service.get_user(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_data

@router.get("/users/", response_model=list[UserResponse])
def read_all_users(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)
    users = service.get_user_all()
    return users

@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_data: UserUpdate, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)
    
    updated_user = service.update_user(user_id=user_id, user_data=user_data)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user

@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    service = UserService(db)
    
    if not service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    service = UserService(db)
    user = db.query(DBUser).filter(DBUser.email == form_data.username).first()  # Use 'username' as 'email'
    
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = service.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}