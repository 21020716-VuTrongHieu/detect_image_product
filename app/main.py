import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from contextlib import asynccontextmanager
import app.services.setup_models as setup_models
from fastapi import FastAPI
from app.routers import router
from app.consumers.rabbitmq_connection import start_consumer
from app.services.redis_client import RedisClient
from app.middlewares.auth import AuthMiddleware
import asyncio
from aiomonitor import start_monitor

@asynccontextmanager
async def lifespan(app: FastAPI):
  monitor = start_monitor(loop=asyncio.get_event_loop(), port=6023)
  # Setup redis client
  RedisClient()
  # Ensure models
  setup_models.ensure_models()
  start_consumer()
  yield
  monitor.close()

app = FastAPI(title="Dectect Image API", version="1.0.0", lifespan=lifespan)
# app.add_middleware(AuthMiddleware)

app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
