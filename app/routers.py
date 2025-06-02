from fastapi import APIRouter, Request, Depends, Path
from app.middlewares.secret import verify_secret_key
from app.controllers import user_controller, variation_controller
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()
# Scopes: /api/v1/user
user_router = APIRouter(prefix="/user", tags=["user"])

@user_router.get("/test")
async def test():
  return await user_controller.test()

router.include_router(user_router)
page_router = APIRouter(prefix="/{page_id}", tags=["page"])

#Scopes: /api/v1/{page_id}/variation
variation_router = APIRouter(prefix="/variation", tags=["variation"])
@variation_router.post("/upload")
async def upload(
  page_id: str = Path(...),
  request: Request = None, 
  db: Session = Depends(get_db),
  _=Depends(verify_secret_key)
):
  body = await request.json()
  body["page_id"] = page_id
  return await variation_controller.upload(body, db)

@variation_router.post("/find")
async def find(
  page_id: str = Path(...),
  request: Request = None, 
  db: Session = Depends(get_db),
  _=Depends(verify_secret_key)
):
  body = await request.json()
  body["page_id"] = page_id
  return await variation_controller.find(body, db)

@variation_router.post("/get_category")
async def get_category(
  page_id: str = Path(...),
  request: Request = None, 
  db: Session = Depends(get_db),
  _=Depends(verify_secret_key)
):
  body = await request.json()
  body["page_id"] = page_id
  return await variation_controller.get_category(body, db)

@variation_router.post("/get_sync_status")
async def get_sync_status(
  page_id: str = Path(...),
  request: Request = None,
  db: Session = Depends(get_db),
  _=Depends(verify_secret_key)
):
  body = await request.json()
  body["page_id"] = page_id
  return await variation_controller.get_sync_status(body, db)

@variation_router.post("/clear_page_shop_variation")
async def clear_page_shop_variation(
  page_id: str = Path(...),
  request: Request = None, 
  db: Session = Depends(get_db),
  _=Depends(verify_secret_key)
):
  body = await request.json()
  body["page_id"] = page_id
  return await variation_controller.clear_page_shop_variation(body, db)

page_router.include_router(variation_router)
router.include_router(page_router)
