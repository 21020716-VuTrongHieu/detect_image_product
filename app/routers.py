from fastapi import APIRouter, Request, Depends
from app.controllers import user_controller, file_controller
from sqlalchemy.orm import Session
from app.database import get_db

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
async def upload(request: Request, db: Session = Depends(get_db)):
  body = await request.json()
  return await file_controller.upload(body, db)

@file_router.post("/find")
async def find(request: Request, db: Session = Depends(get_db)):
  body = await request.json()
  return await file_controller.find(body, db)

@file_router.post("/get_category")
async def get_category(request: Request, db: Session = Depends(get_db)):
  body = await request.json()
  return await file_controller.get_category(body, db)

router.include_router(file_router)
