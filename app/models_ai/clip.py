import os
import torch
import clip
import requests
from PIL import Image
import io

def pad_to_square(image, background_color=(255, 255, 255)):
  w, h = image.size
  if w == h:
      return image
  size = max(w, h)
  new_img = Image.new("RGB", (size, size), background_color)
  new_img.paste(image, ((size - w) // 2, (size - h) // 2))
  return new_img

def predict_product_category(image_path, product_name):
  main_categories = {
    "Clothing": ["a person wearing a dress"],
  }

  try:
    if image_path.startswith("http"):
      response = requests.get(image_path, timeout=10)
      response.raise_for_status()
      image = Image.open(io.BytesIO(response.content)).convert("RGB")
    else:
      image = Image.open(image_path).convert("RGB")
  except Exception as e:
    print(f"Error loading image: {e}")
    return None
  clip_instance = Clip.get_instance()

  group_prompts = [f"{group}" for group in main_categories]
  selected_prompt = clip_instance.predict_from_texts(image, group_prompts)
  print(f"selected_prompt = {selected_prompt}")
  group_name = selected_prompt

  detail_labels = main_categories[group_name]
  detail_prompts = [f"{label}" for label in detail_labels]
  final_prompt = clip_instance.predict_from_texts(image, detail_prompts)
  print(f"final_prompt = {final_prompt}")
  return final_prompt

class Clip:
  _instance = None

  @staticmethod
  def get_instance():
    """Static access method."""
    if Clip._instance is None:
      Clip._instance = Clip()
    return Clip._instance
  
  def __init__(self):
    if Clip._instance is not None:
      raise Exception("This class is a singleton!")
    
    HOME = os.path.dirname(os.path.abspath(__file__))
    while os.path.basename(HOME) != "app":
      HOME = os.path.dirname(HOME)
    
    WEIGHTS_FOLDER = os.path.join(HOME, "models_ai", "weights")
    CLIP_WEIGHTS_PATH = os.path.join(WEIGHTS_FOLDER, "ViT-L-14-336px.pt")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    clip_model, preprocess = clip.load(CLIP_WEIGHTS_PATH, device=device)
    self.model = clip_model
    self.device = device
    self.preprocess = preprocess
    self.model.eval()

  def extract_features(self, images):
    features = []
    for image in images:
      if not isinstance(image, torch.Tensor):
        # image = pad_to_square(image)
        image = self.preprocess(image).unsqueeze(0)
      image = image.to(self.device)
      with torch.no_grad():
        feature_vector = self.model.encode_image(image)
      features.append(feature_vector)
    features = torch.stack(features).squeeze(1)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().tolist()

  def predict_from_texts(self, image, texts):
    if not isinstance(image, torch.Tensor):
      # image = pad_to_square(image)
      image = self.preprocess(image).unsqueeze(0)
    image = image.to(self.device)

    print(f"texts: {texts}")

    text_tokens = clip.tokenize(texts).to(self.device)
    with torch.no_grad():
      image_features = self.model.encode_image(image)
      text_features = self.model.encode_text(text_tokens)
    
    image_features /= image_features.norm(dim=-1, keepdim=True)
    text_features /= text_features.norm(dim=-1, keepdim=True)

    print("Image feature norm:", image_features.norm())
    print("Text feature norm:", text_features.norm())

    similarity = (image_features @ text_features.T).squeeze(0)
    print(f"similarity: {similarity}")
    best_idx = similarity.argmax().item()
    return texts[best_idx]
      
  def get_model(self):
    return self.model
  
  def get_preprocess(self):
    return self.preprocess
  
  def get_device(self):
    return self.device