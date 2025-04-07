import os
import asyncio
from contextlib import asynccontextmanager
import app.services.setup_models as setup_models
from fastapi import FastAPI
from app.routers import router
from app.consumers.rabbitmq_connection import start_consumer
from app.middlewares.auth import AuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
  # Setup models when the app starts
  setup_models.ensure_models()
  start_consumer()
  yield
  # Cleanup code can be added here if needed

app = FastAPI(title="Dectect Image API", version="1.0.0", lifespan=lifespan)
# app.add_middleware(AuthMiddleware)

app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
