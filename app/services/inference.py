from app.models_ai.grounding_dino import GroundingDino
from app.models_ai.marqo_ecommerce_embeddings import MarqoEcommerceEmbeddings, predict_product_category

def process_image(image_path, text_prompt, is_import_data=False):
  
  grounding_dino = GroundingDino.get_instance()
  marqo_ecommerce_embeddings = MarqoEcommerceEmbeddings.get_instance()
  boxes_pixel, logits, phrases, cropped_images = grounding_dino.detect_objects(image_path, text_prompt, is_import_data)

  # save_dir = "cropped_images"
  # os.makedirs(save_dir, exist_ok=True)
  # labels_file = os.path.join(save_dir, "labels.txt")
  # with open(labels_file, "a") as f:
  #   for i, (img, label) in enumerate(zip(cropped_images, phrases)):
  #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
  #     filename = f"{timestamp}_{i}.jpg"
  #     save_path = os.path.join(save_dir, filename)
      
  #     img.save(save_path)
  #     f.write(f"{filename}: {label}\n")
  
  if len(cropped_images) == 0:
    return boxes_pixel, logits, phrases, []
  
  features = marqo_ecommerce_embeddings.extract_features(cropped_images)
  return boxes_pixel, logits, phrases, features

def get_default_phrases(image_path):
  # print(f"image_path: {image_path}")
  list_phrases = predict_product_category(image_path)
  # print(f"list_phrases = {list_phrases}")
  return list_phrases or []