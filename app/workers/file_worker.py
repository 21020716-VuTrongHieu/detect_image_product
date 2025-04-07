from app.services.inference import process_image
from models import ShopVariationVector
from app.database import get_db
from sqlalchemy.orm import Session
import numpy as np

def upload(obj):

  db: Session = next(get_db())

  print(f"Upload Test: {obj}")
  file_path = obj.get("file_path")
  phrase = obj.get("phrase", "object")
  shop_id = obj.get("shop_id")
  variation_id = obj.get("variation_id")
  product_id = obj.get("product_id")

  boxes_pixel, logits, phrases, features = process_image(file_path, phrase, True)

  print("🔹 Bounding Boxes:", boxes_pixel)
  print("🔹 Logits:", logits)
  print("🔹 Phrases:", phrases)
  print("🔹 Feature Vectors Shape:", len(features), "x", len(features[0]) if features else 0)

  if len(features) == 0:
    return None
  
  existing_records = db.query(ShopVariationVector).filter(
    ShopVariationVector.shop_id == shop_id,
    ShopVariationVector.variation_id == variation_id,
    ShopVariationVector.product_id == product_id
  ).all()
  if existing_records:
    print("🔹 Found existing records, deleting...")
    for record in existing_records:
      db.delete(record)
    db.commit()
    print("🔹 Deleted existing records.")

  for i in range(len(features)):
    vector = features[i].tolist() if hasattr(features[i], 'tolist') else features[i]
    logit = logits[i].tolist() if hasattr(logits[i], 'tolist') else logits[i]
    bounding_box = boxes_pixel[i].tolist() if hasattr(boxes_pixel[i], 'tolist') else boxes_pixel[i]
    phrase = phrases[i]

    # Đảm bảo vector có dạng numpy array và đúng chiều
    vector = np.array(vector).tolist()
    shop_variation_vector = ShopVariationVector(
      product_id=product_id,
      variation_id=variation_id,
      shop_id=shop_id,
      vector=vector,
      logit=logit,
      phrase=phrase,
      bounding_box=bounding_box
    )
    db.add(shop_variation_vector)
  db.commit()
  db.refresh(shop_variation_vector)
  print("🔹 Saved to DB:", shop_variation_vector)
