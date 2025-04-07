import app.tools as tools
from app.consumers.rabbitmq_publisher import enqueue

async def test():
  task = {
    "action": "test",
    "payload": {
      "image_path": "https://content.pancake.vn/2-25/2025/4/4/a44f62d83dcea4c91076c3ab1b3fd7c8d99e2971.png",
      "text_prompt": "I want to buy the pink one"
    }
  }
  enqueue("task_pool", task)
  return {"message": "User Test hihi kkk"}