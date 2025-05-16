import os
import torch
from transformers import AutoModel, AutoProcessor
import requests
from PIL import Image
from typing import List, Union

def predict_product_category(image_path):
  main_categories = {
    "clothing": ["dress", "shirt", "pants", "shoes", "hat", "socks", "jacket", "sweater", "shorts", "skirt"],
    "cosmetic": ["lipstick", "foundation", "eyeshadow", "blush", "mascara", "nail polish", "perfume", "skincare", "hair care"],
    "electronics": ["phone", "laptop", "tablet", "camera", "headphones", "smartwatch", "television", "speaker", "charger"],
    "furniture": ["sofa", "table", "chair", "bed", "desk", "shelf", "cabinet", "lamp", "rug"],
  }

  try:
    if image_path.startswith("http"):
      image = Image.open(requests.get(image_path, stream=True).raw).convert("RGB")
    else:
      image = Image.open(image_path).convert("RGB")
  except Exception as e:
    print(f"Error loading image: {e}")
    return None
  
  marqo = MarqoEcommerceEmbeddings.get_instance()
  main_labels = list(main_categories.keys())
  selected_main = marqo.predict_from_texts(image, main_labels)

  if not selected_main:
    return None
  
  sub_labels = []
  for cat in selected_main:
    sub_labels.extend(main_categories.get(cat, []))

  selected_sub = marqo.predict_from_texts(image, sub_labels) if sub_labels else []
  return selected_main + selected_sub

class MarqoEcommerceEmbeddings:
  _instance = None

  THRESHOLD_PHRASE = 0.6
  
  @staticmethod
  def get_instance():
    if MarqoEcommerceEmbeddings._instance is None:
      MarqoEcommerceEmbeddings._instance = MarqoEcommerceEmbeddings()
    return MarqoEcommerceEmbeddings._instance
  
  def __init__(self):
    if MarqoEcommerceEmbeddings._instance is not None:
      raise Exception("This class is a singleton!")
    
    model_name= 'Marqo/marqo-ecommerce-embeddings-L'
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    self.model = model.to(self.device)
    self.processor = processor
    self.model.eval()

  def extract_features(
      self,
      images: List[Union[str, Image.Image]]
  ) -> List[torch.Tensor]:
    pil_images = []
    for image in images:
      if isinstance(image, str):
        image = Image.open(image).convert("RGB")
      elif isinstance(image, Image.Image):
        image = image.convert("RGB")
      else:
        continue
      pil_images.append(image)

    inputs = self.processor(
      images=pil_images, 
      return_tensors="pt", 
      padding=True
    )
    inputs = {k: v.to(self.device) for k, v in inputs.items()}
    with torch.no_grad():
      image_embeddings = self.model.get_image_features(pixel_values=inputs['pixel_values'], normalize=True)

    feature_list = [emb.cpu() for emb in image_embeddings]
    return feature_list
      
  
  def predict_from_texts(self, image, texts):
    # self.processor.image_processor.do_rescale = False
    processed = self.processor(text=texts, images=[image], padding='max_length', return_tensors='pt')
    processed = {k: v.to(self.device) for k, v in processed.items()}

    with torch.no_grad():
      image_features = self.model.get_image_features(processed['pixel_values'], normalize=True)
      text_features = self.model.get_text_features(processed['input_ids'], normalize=True)

      similarity = (100 * image_features @ text_features.T).softmax(dim=-1)
      similarity_scores = similarity[0].tolist()

    return [text for text, score in zip(texts, similarity_scores) if score > self.THRESHOLD_PHRASE]
  
