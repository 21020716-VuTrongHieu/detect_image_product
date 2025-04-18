from fastapi import APIRouter, Request
from app.controllers import user_controller, file_controller

router = APIRouter()

# Scopes: /api/v1/user
user_router = APIRouter(prefix="/user", tags=["user"])

@user_router.get("/test")
async def test():
  return await user_controller.test()

router.include_router(user_router)

#Scopes: /api/v1/file
file_router = APIRouter(prefix="/file", tags=["file"])
@file_router.post("/upload")
async def upload(request: Request):
  body = await request.json()
  return await file_controller.upload(body)

@file_router.post("/find")
async def find(request: Request):
  body = await request.json()
  return await file_controller.find(body)

router.include_router(file_router)
