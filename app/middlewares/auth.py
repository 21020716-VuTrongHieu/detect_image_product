import os
from fastapi import Request, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
  def __init__(self, app):
    super().__init__(app)

  async def dispatch(self, request: Request, call_next):
    token = request.headers.get("Authorization")
    
    if not token:
      raise HTTPException(status_code=401, detail="Missing Authorization Header")

    if not self.validate_token(token):
      raise HTTPException(status_code=403, detail="Invalid Token")

    response = await call_next(request)
    return response

  def validate_token(self, token: str) -> bool:
    
    return True