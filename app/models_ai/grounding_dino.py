import os
import requests
from io import BytesIO
import torch
import groundingdino
from groundingdino.util.inference import load_model, predict, load_image
from PIL import Image, ImageEnhance
import numpy as np
from collections import defaultdict

def prepare_image_for_grounding_dino(url):
  response = requests.get(url)
  img = Image.open(BytesIO(response.content))

  # Convert sang RGB để loại bỏ alpha
  img = img.convert("RGB")

  # Resize để đồng bộ
  img = img.resize((1024, int(1024 * img.height / img.width)))

  # Tăng độ tương phản nhẹ
  contrast = ImageEnhance.Contrast(img)
  img = contrast.enhance(1.2)

  # Tăng độ sắc nét
  sharpness = ImageEnhance.Sharpness(img)
  img = sharpness.enhance(1.3)

  return img

class GroundingDino:
  _instance = None

  BOX_THRESHOLD_IMPORT = 0.3
  TEXT_THRESHOLD_IMPORT = 0.3
  BOX_THRESHOLD_EXPORT = 0.3
  TEXT_THRESHOLD_EXPORT = 0.3
  TOP_K = 1

  @staticmethod
  def get_instance():
    """Static access method."""
    if GroundingDino._instance is None:
      GroundingDino._instance = GroundingDino()
    return GroundingDino._instance
  
  def __init__(self):
    if GroundingDino._instance is not None:
      raise Exception("This class is a singleton!")
    
    HOME = os.path.dirname(os.path.abspath(__file__))
    while os.path.basename(HOME) != "app":
      HOME = os.path.dirname(HOME)
    
    WEIGHTS_FOLDER = os.path.join(HOME, "models_ai", "weights")
    GROUNDINGDINO_PATH = os.path.dirname(groundingdino.__file__)
    GROUNDINGDINO_CONFIG_PATH = os.path.join(GROUNDINGDINO_PATH, "config", "GroundingDINO_SwinB_cfg.py")
    GROUNDINGDINO_WEIGHTS_PATH = os.path.join(WEIGHTS_FOLDER, "groundingdino_swinb_cogcoor.pth")

    model = load_model(GROUNDINGDINO_CONFIG_PATH, GROUNDINGDINO_WEIGHTS_PATH)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"decive {device}")
    self.model = model
    self.device = device
    self.model.eval()

  def detect_objects(self, image_path, text_prompts, is_import_data=False):
    # Load image
    try: 
      if image_path.startswith("http"):
        response = requests.get(image_path, timeout=10)
        response.raise_for_status()
        image_source = prepare_image_for_grounding_dino(image_path)
        image_source = np.array(image_source)
        image = torch.tensor(image_source, dtype=torch.float32).permute(2, 0, 1) / 255.0
        image = (image - torch.tensor([0.485, 0.456, 0.406])[:, None, None]) / torch.tensor([0.229, 0.224, 0.225])[:, None, None]
      else:
        image_source, image = load_image(image_path)
    except Exception as e:
      print(f"Error loading image: {e}")
      return None, None, None, []

    # if is_import_data:
    text_prompt_list = [prompt.strip() for prompt in text_prompts.split(",")]
    # else:
    #   text_prompt_list = [text_prompts.strip()]

    results = []
    H, W, _ = image_source.shape

    for prompt in text_prompt_list:
      print(f"prompt: {prompt}")
      boxes, logits, phrases = predict(
        model=self.model,
        image=image,
        caption=prompt,
        box_threshold=self.BOX_THRESHOLD_IMPORT if is_import_data else self.BOX_THRESHOLD_EXPORT,
        text_threshold=self.TEXT_THRESHOLD_IMPORT if is_import_data else self.TEXT_THRESHOLD_EXPORT,
        device=self.device
      )
      print(f"🔹 phrases: {phrases}")
      print(f"🔹 logits: {logits}")

      if len(boxes) == 0 or len(logits) == 0 or len(phrases) == 0:
        continue

      if is_import_data:
        phrase_groups = defaultdict(list)
        for i, phrase in enumerate(phrases):
          phrase_groups[phrase].append((logits[i], i))

        selected_indices = []
        for phrase, logit_list in phrase_groups.items():
          logit_list.sort(reverse=True, key=lambda x: x[0])
          top_k = min(len(logit_list), self.TOP_K)
          selected_indices.extend([idx for _, idx in logit_list[:top_k]])

        selected_indices = sorted(selected_indices)

        filtered_boxes = boxes[selected_indices]
        filtered_logits = logits[selected_indices]
        filtered_phrases = [phrases[i] for i in selected_indices]
      
      else:
        filtered_boxes = boxes
        filtered_logits = logits
        filtered_phrases = phrases

      boxes_pixel = filtered_boxes.clone()
      boxes_pixel[:, [0, 2]] *= W
      boxes_pixel[:, [1, 3]] *= H
      

      cropped_images = []
      for i, (x_c, y_c, w, h) in enumerate(boxes_pixel):
        x1 = max(int(x_c - w / 2), 0)
        y1 = max(int(y_c - h / 2), 0)
        x2 = min(int(x_c + w / 2), W)
        y2 = min(int(y_c + h / 2), H)
    
        if isinstance(image_source, np.ndarray):
          image_source_pil = Image.fromarray(image_source)
        else:
          image_source_pil = image_source

        cropped_img = image_source_pil.crop((x1, y1, x2, y2))
        cropped_images.append(cropped_img)

      results.append((filtered_boxes, filtered_logits, filtered_phrases, cropped_images))

    print("🔹 results:", results)

    if not results:
      print("🔹 No valid results found.")
      final_boxes = torch.tensor([[0, 0, W, H]], dtype=torch.float32)
      final_logits = torch.zeros((1,))
      final_phrases = ["all image"]
      final_cropped_images = [Image.fromarray(image_source)]
      return final_boxes, final_logits, final_phrases, final_cropped_images

    final_boxes = torch.cat([r[0] for r in results], dim=0)
    final_logits = torch.cat([r[1] for r in results], dim=0)
    final_phrases = sum([r[2] for r in results], [])
    final_cropped_images = sum([r[3] for r in results], [])
    
    return final_boxes, final_logits, final_phrases, final_cropped_images
  
  def get_model(self):
    return self.model
  
  def get_device(self):
    return self.device
