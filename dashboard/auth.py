import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# --- Configuration ---
# It's recommended to set this in your .env file for production
SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "a-super-secret-key-that-should-be-changed")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8 # 8-hour session

# Path to the simple JSON user database
USERS_DB_FILE = os.path.join(os.path.dirname(__file__), "users.json")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# This tells FastAPI's dependency injection system where the login endpoint is.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/dashboard/token")

# --- Pydantic Models for Auth ---
class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str

# --- User Database Functions (using a simple JSON file) ---

def load_users_db() -> Dict[str, Any]:
    """Loads the user database from a JSON file."""
    if not os.path.exists(USERS_DB_FILE):
        return {"users": []}
    try:
        with open(USERS_DB_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"users": []}

def save_users_db(db: Dict[str, Any]):
    """Saves the user database to a JSON file."""
    with open(USERS_DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(username: str) -> Optional[UserInDB]:
    """Retrieves a user from the database by username."""
    db = load_users_db()
    for user_dict in db.get("users", []):
        if user_dict.get("username") == username:
            return UserInDB(**user_dict)
    return None

def create_user(user: UserCreate) -> UserInDB:
    """Creates a new user and saves them to the database."""
    db = load_users_db()
    if get_user(user.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    user_in_db = UserInDB(username=user.username, hashed_password=hashed_password)
    
    db["users"].append(user_in_db.model_dump())
    save_users_db(db)
    return user_in_db

# --- Password & Token Utility Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- FastAPI Authentication Dependency ---

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    A dependency function to validate the token and return the current user.
    This will be used to protect endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return User(username=user.username)