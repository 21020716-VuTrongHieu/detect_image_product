from app.consumers.rabbitmq_publisher import enqueue
from app.services.inference import process_image
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import ShopVariationVector
import numpy as np
from pgvector.sqlalchemy import Vector
from app.crud.shop_variation_vector import find_similar_vectors

async def upload(body):
  """
  Upload a file to the server.
  """

  data = body.get("data", [])
  phrase = body.get("phrase", "object")

  if not data:
    return {"success": False, "message": "No data provided"}
  else:
    for item in data:
      if not isinstance(item, dict):
        continue
      else:
        file_paths = item.get("url", [])
        shop_id = item.get("shop_id")
        variation_id = item.get("variation_id")
        product_id = item.get("product_id")
        if not file_paths or not isinstance(file_paths, list):
          continue
        else:
          for file_path in file_paths:
            if not isinstance(file_path, str):
              continue
            else:
              task = {
                "action": "upload",
                "payload": {
                  "file_path": file_path,
                  "phrase": phrase,
                  "shop_id": shop_id,
                  "variation_id": variation_id,
                  "product_id": product_id
                }
              }
              enqueue("task_pool", task)
    return {"success": True, "message": "File upload task enqueued successfully"}
  
async def find(body):
  """
  Find a file on the server.
  """
  url = body.get("url")
  prompt = body.get("prompt")
  if not url or not isinstance(url, str):
    return {"success": False, "message": "Invalid URL"}
  else:
    boxes_pixel, logits, phrases, features = process_image(url, prompt, False)
    if len(features) == 0:
      return {"success": False, "message": "No features found"}
    
    db: Session = next(get_db())
    closest_records = []
    closest_map = {}

    print(f"phrases: {phrases}")
    print(f"logits: {logits}")

    

    for feature in features:
      vector_data = np.array(feature)
      vector_to_compare_list = vector_data.tolist()

      # Find similar vectors in the database
      results = find_similar_vectors(
        db=db,
        vector=vector_to_compare_list
      )

      if results:
        for shop_id, product_id, variation_id, distance in results:
          key = (shop_id, product_id, variation_id)
          if key not in closest_map or distance < closest_map[key]["distance"]:
            closest_map[key] = {
              "shop_id": shop_id,
              "product_id": product_id,
              "variation_id": variation_id,
              "distance": distance
            }

    closest_records = list(closest_map.values())
    # Sort the closest records by distance
    closest_records.sort(key=lambda x: x["distance"])

    return {"success": True, "data": closest_records}