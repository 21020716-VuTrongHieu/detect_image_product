import os
import torch
from PIL import Image
from torchvision import transforms

def pad_to_square(image, background_color=(255, 255, 255)):
  w, h = image.size
  if w == h:
      return image
  size = max(w, h)
  new_img = Image.new("RGB", (size, size), background_color)
  new_img.paste(image, ((size - w) // 2, (size - h) // 2))
  return new_img

dinov2_transform = transforms.Compose([
  transforms.Resize(518, interpolation=3),
  transforms.ToTensor(),
  transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225]),
])

class DinoV2:
  _instance = None

  @staticmethod
  def get_instance():
    """Static access method."""
    if DinoV2._instance is None:
      DinoV2._instance = DinoV2()
    return DinoV2._instance
  
  def __init__(self):
    if DinoV2._instance is not None:
      raise Exception("This class is a singleton!")
    
    HOME = os.path.dirname(os.path.abspath(__file__))
    while os.path.basename(HOME) != "app":
      HOME = os.path.dirname(HOME)
    
    WEIGHTS_FOLDER = os.path.join(HOME, "models_ai", "weights")
    DINOV2_WEIGHTS_PATH = os.path.join(WEIGHTS_FOLDER, "dinov2_vitg14_pretrain.pth")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    self.device = device
    model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitg14', pretrained=False)
    checkpoint = torch.load(DINOV2_WEIGHTS_PATH, map_location=self.device)
    if isinstance(checkpoint, dict) and 'model' in checkpoint:
      model.load_state_dict(checkpoint['model'])
    else:
      model.load_state_dict(checkpoint)
    self.model = model.to(device)
    self.model.eval()

  def extract_features(self, images):
    features = []
    for image in images:
      image = pad_to_square(image)
      img_tensor = dinov2_transform(image).unsqueeze(0).to(self.device)
      with torch.no_grad():
        feature_vector = self.model(img_tensor)
      features.append(feature_vector)
    features = torch.stack(features).squeeze(1)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().tolist()
  
  def get_model(self):
    return self.model
  