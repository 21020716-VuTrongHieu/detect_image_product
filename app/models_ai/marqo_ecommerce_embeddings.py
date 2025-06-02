import os
import torch
from transformers import AutoModel, AutoProcessor
import requests
from PIL import Image
from typing import List, Union

def predict_product_category(image_path):
  main_categories = {
    "clothing": [
      "dress", "shirt", "t-shirt", "blouse", "pants", "jeans", "shorts", "skirt", "jacket", "coat", "sweater", "hoodie","shoes", "sandals", "boots", "sneakers", "hat", "cap", "socks", "underwear", "bra", "scarf", "belt", "gloves"
    ],
    "cosmetic": [
      "lipstick", "eyeshadow", "blush", "mascara", "eyeliner", "foundation", "nail polish", "perfume", "facial cleanser", "moisturizer", "sunscreen", "toner", "serum", "face mask", "shampoo", "conditioner", "hair oil"
    ],
    "electronics": [
      "smartphone", "laptop", "tablet", "camera", "headphones", "earbuds", "smartwatch", "television", "monitor", "mouse", "keyboard", "speaker", "router", "charger", "power bank", "gamepad", "e-reader", "drone"
    ],
    "furniture": [
      "sofa", "table", "chair", "bed", "desk", "bookshelf", "cabinet", "wardrobe", "lamp", "rug", "mirror", "shoe rack", "tv stand"
    ],
    "home_appliances": [
      "fan", "air conditioner", "refrigerator", "microwave", "rice cooker", "electric kettle", "blender", "vacuum cleaner", "washing machine", "hair dryer", "iron", "water heater"
    ],
    "toys": [
      "doll", "lego", "stuffed animal", "puzzle", "board game", "action figure", "rc car", "building blocks", "playdough"
    ],
    "baby_products": [
      "diapers", "baby bottle", "pacifier", "baby stroller", "crib", "baby clothes", "baby shampoo", "baby wipes", "baby toy"
    ],
    "sports": [
      "bicycle", "treadmill", "dumbbell", "yoga mat", "helmet", "basketball", "football", "tennis racket", "swimsuit", "sports shoes", "gym bag"
    ],
    "automotive": [
      "motor oil", "car vacuum", "car charger", "dashboard camera", "car seat", "helmet", "motorcycle gloves", "car tire", "car cover"
    ],
    "groceries": [
      "instant noodles", "rice", "coffee", "tea", "snacks", "chocolate", "cereal", "milk", "canned food", "cooking oil", "condiments", "bottle water"
    ],
    "stationery": [
      "notebook", "pen", "pencil", "eraser", "ruler", "highlighter", "stapler", "paper", "binder", "scissors", "glue", "tape"
    ],
    "pet_supplies": [
      "pet food", "dog leash", "cat litter", "pet bed", "pet toy", "pet shampoo", "pet carrier", "feeding bowl", "scratch post"
    ],
    "accessories": [
      "backpack", "handbag", "wallet", "watch", "sunglasses", "necklace", "ring", "bracelet", "earrings", "keychain", "hat", "cap"
    ]
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
  
