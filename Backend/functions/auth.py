from database.db import users_collection
from models.user_model import User
from passlib.context import CryptContext
import jwt
import os
from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

def create_user(user: User):
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        return {"error": "User already exists"}
    
    user.password = hash_password(user.password)
    users_collection.insert_one(user.dict())
    return {"message": "User created successfully"}

def authenticate_user(email: str, password: str):
    user = users_collection.find_one({"email": email})
    if not user or not verify_password(password, user["password"]):
        return None

    token = jwt.encode({"email": email}, SECRET_KEY, algorithm="HS256")
    return {"token": token}
security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["email"]
    except:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )