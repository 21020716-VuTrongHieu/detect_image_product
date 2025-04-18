from app.consumers.rabbitmq_publisher import enqueue
from app.services.inference import process_image
from app.database import get_db
from sqlalchemy.orm import Session
import numpy as np
from app.crud.shop_variation_vector import find_similar_vectors
from collections import defaultdict

async def upload(body):
  """
  Upload a file to the server.
  """

  data = body.get("data", [])

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
        meta_data = item.get("meta_data")
        phrase = item.get("phrase", "clothing")
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
                  "product_id": product_id,
                  "meta_data": meta_data
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
  shop_id = body.get("shop_id")
  if not url or not isinstance(url, str):
    return {"success": False, "message": "Invalid URL"}
  else:
    boxes_pixel, logits, phrases, features = process_image(url, prompt, True)
    if len(features) == 0:
      return {"success": False, "message": "No features found"}
    
    db: Session = next(get_db())
    print(f"phrases: {phrases}")
    print(f"logits: {logits}")

    all_records = []
    

    for i, feature in enumerate(features):
      vector_data = np.array(feature)
      vector_to_compare_list = vector_data.tolist()

      results = find_similar_vectors(
        db=db,
        vector=vector_to_compare_list,
        shop_id=shop_id,
        limit=1000,
        threshold=0.26
      )

      phrase = phrases[i]
      logit = logits[i]

      for res in results:
        shop_id_r, product_id, variation_id, meta_data, _, _, distance = res
        print(f"variation_id: {variation_id}, distance: {distance}")
        all_records.append({
          "shop_id": shop_id_r,
          "product_id": product_id,
          "variation_id": variation_id,
          "meta_data": meta_data,
          "phrase": phrase,
          "logit": logit,
          "distance": distance
        })

    best_variation_map = {}
    for record in all_records:
      key = (record["shop_id"], record["product_id"], record["variation_id"])
      if key not in best_variation_map or record["distance"] < best_variation_map[key]["distance"]:
        best_variation_map[key] = record

    grouped_results = defaultdict(list)

    temp_product_grouping = defaultdict(list)

    for record in best_variation_map.values():
      phrase = record["phrase"]
      group_key = (record["shop_id"], record["product_id"], phrase, record["distance"])
      temp_product_grouping[group_key].append(record)

    for group_key, records in temp_product_grouping.items():
      shop_id, product_id, phrase, distance = group_key
      if len(records) == 1:
        grouped_results[phrase].append(records[0])
      else:
        merged = {
          "shop_id": shop_id,
          "product_id": product_id,
          "meta_data": records[0]["meta_data"],
          "phrase": phrase,
          "logit": max(r["logit"] for r in records),
          "distance": distance,
          "variation_ids": [r["variation_id"] for r in records]
        }
        grouped_results[phrase].append(merged)

    final_results = []
    for phrase, records in grouped_results.items():
      records.sort(key=lambda x: x["distance"])
      top_2 = records[:2]
      final_results.extend(top_2)

    final_results.sort(key=lambda x: x["distance"])

    return {"success": True, "data": final_results}