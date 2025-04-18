from app.services.inference import process_image
from models import ShopVariationVector
from app.database import get_db
from sqlalchemy.orm import Session
import numpy as np
import torch

def upload(obj):

  db: Session = next(get_db())

  print(f"Upload Test: {obj}")
  file_path = obj.get("file_path")
  phrase = obj.get("phrase", "object")
  shop_id = obj.get("shop_id")
  variation_id = obj.get("variation_id")
  product_id = obj.get("product_id")
  meta_data = obj.get("meta_data")

  boxes_pixel, logits, phrases, features = process_image(file_path, phrase, True)

  print("🔹 Bounding Boxes:", boxes_pixel)
  print("🔹 Logits:", logits)
  print("🔹 Phrases:", phrases)
  print("🔹 Feature Vectors Shape:", len(features), "x", len(features[0]) if features else 0)

  if len(features) == 0:
    return None

  for i in range(len(features)):
    # Chuyển tensor thành list nếu là tensor, nếu không thì giữ nguyên danh sách
    vector = features[i].cpu().numpy().tolist() if isinstance(features[i], torch.Tensor) else features[i]
    # Các đối tượng khác (logit, bounding_box, ...) không cần thay đổi
    logit = logits[i].cpu().numpy().tolist() if isinstance(logits[i], torch.Tensor) else logits[i]
    bounding_box = boxes_pixel[i].cpu().numpy().tolist() if isinstance(boxes_pixel[i], torch.Tensor) else boxes_pixel[i]
    phrase = phrases[i]

    # Đảm bảo vector có dạng numpy array và đúng chiều
    # vector = np.array(vector).tolist()
    # vector_2 = np.array(vector_2).tolist()

    print("🔹 Vector:", vector)
    shop_variation_vector = ShopVariationVector(
      product_id=product_id,
      variation_id=variation_id,
      shop_id=shop_id,
      vector=vector,
      logit=logit,
      phrase=phrase,
      bounding_box=bounding_box,
      meta_data=meta_data
    )
    db.add(shop_variation_vector)
  db.commit()
  db.refresh(shop_variation_vector)
  print("🔹 Saved to DB:", shop_variation_vector)
