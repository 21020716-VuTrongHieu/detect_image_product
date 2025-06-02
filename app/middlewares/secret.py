import os
from dotenv import load_dotenv
from fastapi import Request, HTTPException
load_dotenv()

async def verify_secret_key(request: Request):
  try:
    body = await request.json()
    secret_key = body.get("secret_key")
    expected_key = os.getenv("DETECT_IMAGE_SECRET_KEY")
    if not secret_key or secret_key != expected_key:
      raise HTTPException(status_code=403, detail="Forbidden: Invalid secret key")
  except Exception as e:
    raise HTTPException(status_code=400, detail=f"Bad Request: {str(e)}")