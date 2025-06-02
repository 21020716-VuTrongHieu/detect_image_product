from app.consumers.rabbitmq_publisher import enqueue
from app.services.inference import process_image, get_default_phrases
from sqlalchemy.orm import Session
import numpy as np
from app.crud.page_variation_vector import find_similar_vectors
from collections import defaultdict
from app.models_ai.marqo_ecommerce_embeddings import predict_product_category
from models import VariationSyncSessions, VariationData, VariationRegions, Regions
from sqlalchemy import update, delete
from app.services.redis_client import RedisClient

redis_client = RedisClient()

async def upload(body: dict, db: Session):
  data = body.get("data", [])

  if not data:
    return {"success": False, "message": "No data provided"}
  
  page_id = body.get("page_id")
  if not page_id:
    return {"success": False, "message": "Invalid page_id"}
  
  valid_tasks = []
  for item in data:
    if not isinstance(item, dict):
      continue
    images = item.get("images", [])
    if not isinstance(images, list) or len(images) == 0:
      continue
    valid_tasks.append(item)

  delta = len(valid_tasks)
  if delta == 0:
    return {"success": False, "message": "No valid data to process"}
  
  session_obj = (
    db.query(VariationSyncSessions)
      .filter(
        VariationSyncSessions.page_id == page_id,
        VariationSyncSessions.status.in_(["pending", "in_progress"])
      )
      .order_by(VariationSyncSessions.created_at.desc())
      .with_for_update(of=VariationSyncSessions)
      .first()
  )
  if not session_obj:
    # clear_all_variation(page_id)  # chú ý đoạn này
    session_obj = VariationSyncSessions(
      page_id=page_id,
      total_variations=0,
      processed_variations=0,
      error_count=0,
      status="pending"
    )
    db.add(session_obj)
    db.flush()
  
  try:
    db.execute(
      update(VariationSyncSessions)
      .where(VariationSyncSessions.id == session_obj.id)
      .values(
        total_variations=VariationSyncSessions.total_variations + delta,
        status="in_progress"
      )
    )
    db.commit()
  except Exception as e:
    db.rollback()
    return {"success": False, "message": str(e)}
  
  redis_key = f"variation_sync_session_{page_id}"
  with redis_client.pipeline() as pipe:
    pipe.hincrby(redis_key, "total_variations", delta)
    pipe.hset(redis_key, "status", "in_progress")
    pipe.hset(redis_key, "session_id", str(session_obj.id))
    pipe.expire(redis_key, 3600)
    pipe.execute()

  for item in valid_tasks:
    task = {
      "action": "upload",
      "payload": {
        "images": item.get("images"),
        "phrase": item.get("phrase"),
        "page_shop_id": item.get("page_shop_id"),
        "variation_id": item.get("variation_id"),
        "product_id": item.get("product_id"),
        "meta_data": item.get("meta_data"),
        "page_id": page_id,
        "page_shop_id": item.get("page_shop_id"),
      }
    }
    enqueue("task_pool", task)

  return {
    "success": True, 
    "message": f"Uploaded {delta} images for processing", 
    "session_id": str(session_obj.id)
  }
# viết lại logic tìm kiếm theo 2 trường page shop id 
async def find(body: dict, db: Session):
  image_path = body.get("image_path")
  phrase = body.get("text_query", [])
  page_id = body.get("page_id")
  shop_id = body.get("shop_id")
  if not image_path or not isinstance(image_path, str):
    return {"success": False, "message": "Invalid image path"}
  else:

    phrase_default = get_default_phrases(image_path)
    if not phrase:
      phrase_list = phrase_default
    elif isinstance(phrase, str):
      phrase_list = list(set([phrase] + phrase_default))
    elif isinstance(phrase, list):
      phrase_list = list(set(phrase + phrase_default))
    else:
      return {"success": False, "message": "Invalid phrase type. Must be str or list."}
    phrase_list.append("full_image")

    print(f"phrase_list: {phrase_list}")

    all_features, all_phrases = [], []

    for item_phrase in phrase_list:
      _, _, phrases, features = process_image(image_path, item_phrase, False)
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
        page_id=page_id,
        shop_id=shop_id,
        limit=1000,
        threshold=0.3
      )

      best_records_map = {}
      for res in results:
        page_id_r, product_id, variation_id, meta_data, distance = res
        key = (page_id_r, product_id, variation_id)
        distance = float(distance)
        if key not in best_records_map or distance < best_records_map[key]["distance"]:
          best_records_map[key] = {
            "page_shop_id": page_id_r,
            "product_id": product_id,
            "variation_id": variation_id,
            "meta_data": meta_data,
            "phrase": phrase,
            "distance": distance,
          }
      all_records.extend(best_records_map.values())

    best_variation_map = {}
    for record in all_records:
      key = (record["page_shop_id"], record["product_id"], record["variation_id"])
      if key not in best_variation_map or record["distance"] < best_variation_map[key]["distance"]:
        best_variation_map[key] = record
    grouped_results = defaultdict(list)
    temp_product_grouping = defaultdict(list)
    for record in best_variation_map.values():
      phrase = record["phrase"]
      group_key = (record["page_shop_id"], record["product_id"], phrase, record["distance"])
      temp_product_grouping[group_key].append(record)
    for group_key, records in temp_product_grouping.items():
      page_shop_id, product_id, phrase, distance = group_key
      if len(records) == 1:
        grouped_results[phrase].append(records[0])
      else:
        merged = {
          "page_shop_id": page_shop_id,
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
  
async def get_sync_status(body: dict, db: Session):
  page_id = body.get("page_id")
  if not page_id:
    return {"success": False, "message": "Invalid page_id"}
  
  session_obj = (
    db.query(VariationSyncSessions)
      .filter(VariationSyncSessions.page_id == page_id)
      .order_by(VariationSyncSessions.created_at.desc())
      .first()
  )
  # if not session_obj:
  #   return {"success": False, "message": "No session found"}
  
  return {
    "success": True,
    "page_id": session_obj.page_id if session_obj else page_id,
    "total_variations": session_obj.total_variations if session_obj else 0,
    "processed_variations": session_obj.processed_variations if session_obj else 0,
    "error_count": session_obj.error_count if session_obj else 0,
    "status": session_obj.status if session_obj else "completed"
  }

async def clear_page_shop_variation(body: dict, db: Session):
  # page_id = body.get("page_id")
  page_shop_id = body.get("page_shop_id")
  if not page_shop_id:
    return {"success": False, "message": "Invalid page_shop_id"}
  try:
    db.execute(
      delete(VariationRegions)
      .where(VariationRegions.page_shop_id == page_shop_id)
    )
    db.execute(
      delete(VariationData)
      .where(VariationData.page_shop_id == page_shop_id)
    )
    db.execute(
      delete(Regions)
      .where(Regions.page_shop_id == page_shop_id)
    )
    db.commit()
  except Exception as e:
    db.rollback()
    return {"success": False, "message": str(e)}
  return {"success": True, "message": "Page shop variation cleared successfully"}
  
async def get_category(body: dict, db: Session):
  url = body.get("url")
  result = predict_product_category(url)
  if result:
    return {"success": True, "data": result}
  else:
    return {"success": False, "message": "No category found"}