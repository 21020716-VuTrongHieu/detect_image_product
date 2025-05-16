from app.services.inference import process_image, get_default_phrases
from models import VariationData, VariationRegions, Regions
from app.database import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
import torch

def upload(obj):
  db: Session = SessionLocal()
  try:
    images = obj.get("images", [])
    phrase = obj.get("phrase")
    shop_id = obj.get("shop_id")
    variation_id = obj.get("variation_id")
    product_id = obj.get("product_id")
    meta_data = obj.get("meta_data")

    clean_old_variation(db, shop_id, variation_id)
    if len(images) != 0:
      variation_data = VariationData(
        product_id=product_id,
        variation_id=variation_id,
        shop_id=shop_id,
        meta_data=meta_data
      )
      db.add(variation_data)
      db.flush()
      db.refresh(variation_data)
      
      for image in images:
        if not phrase:
          phrase_list = get_default_phrases(image)
        elif isinstance(phrase, str):
          phrase_list = [phrase]
        elif isinstance(phrase, list):
          phrase_list = phrase
        else:
          continue
        
        phrase_list.append("full_image")
        for item_phrase in phrase_list:
          exists = db.execute(
            select(Regions.id).where(
              Regions.shop_id == shop_id,
              Regions.phrase == item_phrase,
              Regions.image_path == image,
            )
          ).scalars().first()

          if exists:
            variation_region = VariationRegions(
              shop_id=shop_id,
              variation_data_id=variation_data.id,
              region_id=exists
            )
            db.add(variation_region)
            continue

          boxes_pixel, _, phrases, features = process_image(image, item_phrase, True)
          if len(features) == 0:
            continue
          
          for i in range(len(features)):
            vector = features[i].cpu().numpy().tolist() if isinstance(features[i], torch.Tensor) else features[i]
            bounding_box = boxes_pixel[i].cpu().numpy().tolist() if isinstance(boxes_pixel[i], torch.Tensor) else boxes_pixel[i]
            item_phrase = phrases[i]

            region = Regions(
              shop_id=shop_id,
              image_path=image,
              bbox=bounding_box,
              vector=vector,
              phrase=item_phrase,
            )
            db.add(region)
            db.flush()

            variation_region = VariationRegions(
              shop_id=shop_id,
              variation_data_id=variation_data.id,
              region_id=region.id
            )
            db.add(variation_region)

    db.commit()
  except Exception as e:
    db.rollback()
    # raise
  finally:
    db.close()


def clean_old_variation(db: Session, shop_id: int, variation_id: str):
  variation_data_ids = db.execute(
    select(VariationData.id).where(
      VariationData.shop_id == shop_id,
      VariationData.variation_id == variation_id
    )
  ).scalars().all()

  if not variation_data_ids:
    return 
  
  region_ids = db.execute(
    select(VariationRegions.region_id).where(
      VariationRegions.shop_id == shop_id,
      VariationRegions.variation_data_id.in_(variation_data_ids)
    )
  ).scalars().all()

  db.execute(
    delete(VariationRegions).where(
      VariationRegions.shop_id == shop_id,
      VariationRegions.variation_data_id.in_(variation_data_ids)
    )
  )

  db.execute(
    delete(VariationData).where(
      VariationData.shop_id == shop_id,
      VariationData.id.in_(variation_data_ids)
    )
  )

  if region_ids:
    still_used_ids = db.execute(
      select(VariationRegions.region_id).where(
        VariationRegions.shop_id == shop_id,
        VariationRegions.region_id.in_(region_ids)
      )
    ).scalars().all()

    to_delete_region_ids = list(set(region_ids) - set(still_used_ids))
    if to_delete_region_ids:
      db.execute(
        delete(Regions).where(
          Regions.shop_id == shop_id,
          Regions.id.in_(to_delete_region_ids)
        )
      )
