from fastapi import APIRouter, Depends

from app.auth import auth_backend, current_active_user
from app.models.user import User


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/refresh")
async def refresh(user: User = Depends(current_active_user)):
    strategy = auth_backend.get_strategy()
    token = await strategy.write_token(user)
    return {"access_token": token, "token_type": "bearer"}
