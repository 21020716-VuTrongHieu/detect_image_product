from app.consumers.rabbitmq_publisher import enqueue
from app.services.inference import process_image, get_default_phrases
from sqlalchemy.orm import Session
import numpy as np
from app.crud.shop_variation_vector import find_similar_vectors
from collections import defaultdict
from app.models_ai.marqo_ecommerce_embeddings import predict_product_category

async def upload(body: dict, db: Session):
  data = body.get("data", [])

  if not data:
    return {"success": False, "message": "No data provided"}
  
  for item in data:
    if not isinstance(item, dict):
      continue
    
    images = item.get("images", [])
    shop_id = item.get("shop_id")
    variation_id = item.get("variation_id")
    product_id = item.get("product_id")
    meta_data = item.get("meta_data")
    phrase = item.get("phrase")
    if not isinstance(images, list) or len(images) == 0:
      continue
    
    task = {
      "action": "upload",
      "payload": {
        "images": images,
        "phrase": phrase,
        "shop_id": shop_id,
        "variation_id": variation_id,
        "product_id": product_id,
        "meta_data": meta_data
      }
    }
    enqueue("task_pool", task)
  return {"success": True, "message": "File upload task enqueued successfully"}
  
async def find(body: dict, db: Session):
  url = body.get("url")
  phrase = body.get("phrase")
  shop_id = body.get("shop_id")
  if not url or not isinstance(url, str):
    return {"success": False, "message": "Invalid URL"}
  else:

    if not phrase:
      phrase_list = get_default_phrases(url)
    elif isinstance(phrase, str):
      phrase_list = [phrase]
    elif isinstance(phrase, list):
      phrase_list = phrase
    else:
      return {"success": False, "message": "Invalid phrase type. Must be str or list."}
    phrase_list.append("full_image")

    all_features, all_phrases = [], []

    for item_phrase in phrase_list:
      _, _, phrases, features = process_image(url, item_phrase, False)
      if features:
        all_features.extend(features)
        all_phrases.extend(phrases)

    if not all_features:
      return {"success": False, "message": "No features found"}
    
    all_records = []
    for i, feature in enumerate(all_features):
      vector = np.array(feature).tolist()
      phrase = all_phrases[i]

      results = find_similar_vectors(
        db=db,
        vector=vector,
        shop_id=shop_id,
        limit=1000,
        threshold=0.3
      )

      best_records_map = {}
      for res in results:
        shop_id_r, product_id, variation_id, meta_data, distance = res
        key = (shop_id_r, product_id, variation_id)
        distance = float(distance)
        if key not in best_records_map or distance < best_records_map[key]["distance"]:
          best_records_map[key] = {
            "shop_id": shop_id_r,
            "product_id": product_id,
            "variation_id": variation_id,
            "meta_data": meta_data,
            "phrase": phrase,
            "distance": distance,
          }
      all_records.extend(best_records_map.values())

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
          "shop_id": int(shop_id),
          "product_id": product_id,
          "meta_data": records[0]["meta_data"],
          "phrase": phrase,
          "distance": float(distance),
          "variation_ids": [r["variation_id"] for r in records]
        }
        grouped_results[phrase].append(merged)
    final_results = []
    for phrase, records in grouped_results.items():
      records.sort(key=lambda x: x["distance"])
      final_results.extend(records[:2])
    final_results.sort(key=lambda x: x["distance"])
    return {"success": True, "data": final_results}
  
async def get_category(body: dict, db: Session):
  url = body.get("url")
  result = predict_product_category(url)
  if result:
    return {"success": True, "data": result}
  else:
    return {"success": False, "message": "No category found"}