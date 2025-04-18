import os
from app.models_ai.grounding_dino import GroundingDino
from app.models_ai.clip import Clip
from app.models_ai.dinov2 import DinoV2
from datetime import datetime

def process_image(image_path, text_prompt, is_import_data=False):
  # Get instances of the models
  grounding_dino = GroundingDino.get_instance()
  clip = Clip.get_instance()
  # dinov2 = DinoV2.get_instance()

  # Detect objects using GroundingDino
  boxes_pixel, logits, phrases, cropped_images = grounding_dino.detect_objects(image_path, text_prompt, is_import_data)
  # Extract features using CLIP
  if len(cropped_images) == 0:
    return boxes_pixel, logits, phrases, []
  
  features = clip.extract_features(cropped_images)
  # features_2 = dinov2.extract_features(cropped_images)

  # print("🔹 phrases:", phrases)

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

  return boxes_pixel, logits, phrases, features


def setup_models():
  # Setup models
  grounding_dino = GroundingDino.get_instance()
  clip = Clip.get_instance()

  # Warm up the models
  image_path = os.path.join(os.path.dirname(__file__), "test_image.jpg")
  text_prompt = "dog"
  
  # Warm up GroundingDino
  grounding_dino.detect_objects(image_path, text_prompt)

  # Warm up CLIP
  cropped_images = [grounding_dino.get_cropped_image(image_path)]
  clip.extract_features(cropped_images)
