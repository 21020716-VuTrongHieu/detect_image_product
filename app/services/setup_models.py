import os
import concurrent.futures

def download_model(model_name, model_info):
	weight_path = model_info["path"]
	weight_url = model_info["url"]

	if not os.path.exists(weight_path):
		print(f"Downloading {model_name}...")
		os.system(f"wget -q -O {weight_path} {weight_url}")
		print(f"{model_name} downloaded successfully.")
	else:
		print(f"{model_name} already exists.")

def ensure_models():
  HOME = os.path.dirname(os.path.abspath(__file__))
  while os.path.basename(HOME) != "app":
    HOME = os.path.dirname(HOME)

  WEIGHTS_FOLDER = os.path.join(HOME, "models_ai", "weights")
  os.makedirs(WEIGHTS_FOLDER, exist_ok=True)
  MODELS = {
    "GroundingDINO": {
      "path": os.path.join(WEIGHTS_FOLDER, "groundingdino_swinb_cogcoor.pth"),
      "url": "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha2/groundingdino_swinb_cogcoor.pth",
    },
    "CLIP": {
      "path": os.path.join(WEIGHTS_FOLDER, "ViT-L-14-336px.pt"),
      "url": "https://openaipublic.azureedge.net/clip/models/3035c92b350959924f9f00213499208652fc7ea050643e8b385c2dac08641f02/ViT-L-14-336px.pt",
    },
  }
	
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(download_model, name, info): name for name, info in MODELS.items()}

    for future in concurrent.futures.as_completed(futures):
      model_name = futures[future]
      try:
        future.result()
      except Exception as e:
        print(f"Error downloading {model_name}: {e}")

if __name__ == "__main__":
  ensure_models()