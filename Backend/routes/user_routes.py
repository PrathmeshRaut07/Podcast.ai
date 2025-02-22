from fastapi import APIRouter, HTTPException, Depends
from models.user_model import User,LoginRequest
from functions.auth import create_user, authenticate_user
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup")
async def signup(user: User):
    response = create_user(user)
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@router.post("/login")
async def login(request: LoginRequest):
    response = authenticate_user(request.email, request.password)
    if response is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return response
