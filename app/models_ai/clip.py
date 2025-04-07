import os
import torch
import clip

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
        image = self.preprocess(image).unsqueeze(0)
      image = image.to(self.device)
      with torch.no_grad():
        feature_vector = self.model.encode_image(image)
      features.append(feature_vector)
    features = torch.stack(features).squeeze(1)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().tolist()
      
  def get_model(self):
    return self.model
  
  def get_preprocess(self):
    return self.preprocess
  
  def get_device(self):
    return self.device