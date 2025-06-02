import os
from dotenv import load_dotenv
from app.services.inference import process_image, get_default_phrases
from models import VariationData, VariationRegions, Regions, VariationSyncSessions
from app.database import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from app.services.redis_client import RedisClient
from collections import defaultdict
from app.consumers.rabbitmq_publisher import enqueue
from app.tools import get_bot_hostname, http_post_json
load_dotenv()
redis_client = RedisClient()

def upload(obj):
  db: Session = SessionLocal()
  error_occurred = False
  try:
    images = obj.get("images") or []
    phrase = obj.get("phrase")
    page_id = str(obj.get("page_id"))
    page_shop_id = str(obj.get("page_shop_id"))
    variation_id = str(obj.get("variation_id"))
    product_id = str(obj.get("product_id"))
    meta_data = obj.get("meta_data")

    key_upload_variation = f"variation_sync_{page_shop_id}_{product_id}_{variation_id}"
    is_locked = redis_client.set(key_upload_variation, 1, nx=True, ex=60)  # 1 minute expiration
    if not is_locked:
      print(f"Key {key_upload_variation} is already set, skipping this upload.")
      return
    
    clear_old_variation(db, page_shop_id, variation_id)
    if images:
      existed_variation = db.execute(
        select(VariationData.id)
        .where(
          VariationData.page_shop_id == page_shop_id,
          VariationData.product_id == product_id,
          VariationData.variation_id == variation_id
        )
      ).scalar_one_or_none()
      if existed_variation:
        print(f"Variation {variation_id} for product {product_id} already exists in page_shop_id {page_shop_id}.")
        return
      
      variation_data = VariationData(
        product_id=product_id,
        variation_id=variation_id,
        page_shop_id=page_shop_id,
        meta_data=meta_data
      )
      db.add(variation_data)
      db.flush()
      db.refresh(variation_data)
      
      for image_path in images:
        if not phrase:
          phrase_list = get_default_phrases(image_path) or []
        elif isinstance(phrase, str):
          phrase_list = [phrase]
        elif isinstance(phrase, list):
          phrase_list = phrase
        else:
          continue
        
        phrase_list.append("full_image")

        existing_regions = db.execute(
          select(Regions)
          .where(
            Regions.page_shop_id == page_shop_id,
            Regions.phrase.in_(phrase_list),
            Regions.image_path == image_path
          )
        ).scalars().all()

        region_map = defaultdict(list)
        for r in existing_regions:
          region_map[r.phrase].append(r)

        for item_phrase in phrase_list:
          existing = region_map.get(item_phrase, [])
          all_ready = all(r.bbox is not None and r.vector is not None for r in existing) and existing
          # Upsert Region record
          if all_ready:
            for region in existing:
              rel_stmt = (
                insert(VariationRegions)
                .values(
                  page_shop_id=page_shop_id,
                  variation_data_id=variation_data.id,
                  region_id=region.id
                )
                .on_conflict_do_nothing()
              )
              db.execute(rel_stmt)
          else:
            old_region_ids = [r.id for r in existing]
            if old_region_ids:
              db.execute(
                delete(VariationRegions)
                .where(
                  VariationRegions.page_shop_id == page_shop_id,
                  VariationRegions.variation_data_id == variation_data.id,
                  VariationRegions.region_id.in_(old_region_ids)
                )
              )
              db.execute(
                delete(Regions)
                .where(
                  Regions.page_shop_id == page_shop_id,
                  Regions.phrase == item_phrase,
                  Regions.image_path == image_path
                )
              )
            boxes, _, phrases, features = process_image(image_path, item_phrase, True)
            if len(features) == 0:
              continue
            for bbox, feature, ph in zip(boxes, features, phrases):
              vec = feature.cpu().numpy().tolist() if hasattr(feature, 'cpu') else feature.tolist()
              bb = bbox.cpu().numpy().tolist() if hasattr(bbox, 'cpu') else bbox.tolist()

              ins_stmt = (
                insert(Regions)
                .values(
                  page_shop_id=page_shop_id,
                  image_path=image_path,
                  bbox=bb,
                  vector=vec,
                  phrase=ph
                )
                .returning(Regions.id)
              )
              region_id = db.execute(ins_stmt).scalar()
              rel_stmt = (
                insert(VariationRegions)
                .values(
                  page_shop_id=page_shop_id,
                  variation_data_id=variation_data.id,
                  region_id=region_id
                )
                .on_conflict_do_nothing()
              )
              db.execute(rel_stmt)
    db.commit()
  except Exception as e:
    print(f"Error: {e}")
    print(f"Error occurred while processing page_shop_id: {page_shop_id}, variation_id: {variation_id}, product_id: {product_id}")
    db.rollback()
    error_occurred = True
    # raise
  finally:
    if is_locked:
      redis_client.delete(key_upload_variation)
    # Update the Redis key with the total variations
    try:
      task_buffer = {
        "action": "statistic_upload",
        "payload": {
          "page_id": page_id,
          "count_processed":  1,
          "count_error": 1 if error_occurred else 0
        }
      }
      enqueue("task_pool", task_buffer)
    except Exception as redis_error:
      print(f"Redis error: {redis_error}")
      pass
    db.close()

def clear_old_variation(db: Session, page_shop_id: str, variation_id: str):
  old_ids = db.execute(
    select(VariationData.id)
    .where(
      VariationData.page_shop_id == page_shop_id,
      VariationData.variation_id == variation_id
    )
  ).scalars().all()

  if not old_ids:
    return 
  
  region_ids = db.execute(
    select(VariationRegions.region_id)
    .where(
      VariationRegions.page_shop_id == page_shop_id,
      VariationRegions.variation_data_id.in_(old_ids)
    )
  ).scalars().all()
  
  db.execute(
    delete(VariationRegions)
    .where(
      VariationRegions.page_shop_id == page_shop_id,
      VariationRegions.variation_data_id.in_(old_ids)
    )
  )
  db.execute(
    delete(VariationData)
    .where(
      VariationData.page_shop_id == page_shop_id,
      VariationData.id.in_(old_ids)
    )
  )

  if region_ids:
    still_used = db.execute(
      select(VariationRegions.region_id)
      .where(
        VariationRegions.page_shop_id == page_shop_id,
        VariationRegions.region_id.in_(region_ids)
      )
    ).scalars().all()

    to_delete = set(region_ids) - set(still_used)
    if to_delete:
      db.execute(
        delete(Regions)
        .where(
          Regions.page_shop_id == page_shop_id,
          Regions.id.in_(list(to_delete))
        )
      )

def clear_all_variation(page_shop_id: str):
  db: Session = SessionLocal()
  db.execute(
    delete(VariationRegions)
    .where(
      VariationRegions.page_shop_id == page_shop_id
    )
  )
  db.execute(
    delete(VariationData)
    .where(
      VariationData.page_shop_id == page_shop_id
    )
  )
  db.execute(
    delete(Regions)
    .where(
      Regions.page_shop_id == page_shop_id
    )
  )
  db.commit()
  db.close()

def statistic_upload(obj):
  page_id = obj.get("page_id")
  count_processed = obj.get("count_processed", 0)
  count_error = obj.get("count_error", 0)
  redis_key = f"variation_sync_session_{page_id}"
  redis_client.hincrby(redis_key, "processed_variations", count_processed)
  redis_client.hincrby(redis_key, "error_count", count_error)

  total = redis_client.hget(redis_key, "total_variations")
  processed = redis_client.hget(redis_key, "processed_variations")
  if total and processed:
    total = int(total)
    processed = int(processed)
    
    if processed % 10 == 0 or processed >= total:
      update_progress_in_db(page_id)

def update_progress_in_db(page_id: str):
  db: Session = SessionLocal()
  redis_key = f"variation_sync_session_{page_id}"
  processed = redis_client.hget(redis_key, "processed_variations")
  error_count = redis_client.hget(redis_key, "error_count")

  if not processed:
    db.close()
    return

  processed = int(processed)
  error_count = int(error_count) if error_count else 0

  try: 
    row = (
      db.query(VariationSyncSessions)
      .filter(
        VariationSyncSessions.page_id == page_id,
        VariationSyncSessions.status.in_(["pending", "in_progress"])
      )
      .order_by(VariationSyncSessions.created_at.desc())
      .with_for_update(of=VariationSyncSessions)
      .first()
    )

    if not row:
      return
    
    if processed > (row.processed_variations or 0):
      row.processed_variations = processed
      row.error_count = error_count
      row.status = "completed" if processed >= row.total_variations else "in_progress"
      db.commit()
      db.refresh(row)

      url_call_back  = f"{get_bot_hostname()}/pages/{page_id}/ai/update_status_sync_variation"
      body = {
        "secret_key": os.getenv("BOTCAKE_SECRET_KEY"),
        "status": row.status,
        "processed_variations": row.processed_variations,
        "total_variations": row.total_variations,
        "error_count": row.error_count,
        "update_time": row.updated_at.timestamp(),
      }

      http_call = http_post_json(url_call_back, body)
      if not http_call.get("success"):
        task = {
          "action": "update_status_callback",
          "payload": {
            "page_id": page_id,
            "status": row.status,
            "processed_variations": row.processed_variations,
            "total_variations": row.total_variations,
            "error_count": row.error_count,
            "update_time": row.updated_at.timestamp(),
          }
        }
        enqueue("task_pool", task)
      
      if row.processed_variations >= row.total_variations:
        redis_client.delete(redis_key)

    else:
      print("Skipping update, processed count is not greater than the current value.")
  except Exception as e:
    print(f"Error updating progress in DB: {e}")
    db.rollback()
  finally:
    db.close()

def update_status_callback(obj):
  page_id = obj.get("page_id")
  status = obj.get("status")
  processed_variations = obj.get("processed_variations", 0)
  total_variations = obj.get("total_variations", 0)
  error_count = obj.get("error_count", 0)
  retry_count = obj.get("retry_count", 0)
  update_time = obj.get("update_time")

  # Gọi lại Botcake để cập nhật trạng thái
  url_call_back  = f"{get_bot_hostname()}/pages/{page_id}/ai/update_status_sync_variation"
  body = {
    "secret_key": os.getenv("BOTCAKE_SECRET_KEY"),
    "status": status,
    "processed_variations": processed_variations,
    "total_variations": total_variations,
    "error_count": error_count,
    "update_time": update_time,
  }

  http_call = http_post_json(url_call_back, body)
  if not http_call.get("success"):
    # Retry logic
    queue_name = None
    if retry_count == 0:
      queue_name = "wait_sec_05"
    elif retry_count == 1:
      queue_name = "wait_min_01"

    if queue_name:
      task = {
        "action": "update_status_callback",
        "payload": {
          "page_id": page_id,
          "status": status,
          "processed_variations": processed_variations,
          "total_variations": total_variations,
          "error_count": error_count,
          "update_time": update_time,
          "retry_count": retry_count + 1
        }
      }
      enqueue(queue_name, task)
