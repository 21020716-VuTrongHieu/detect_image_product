from app.services.inference import process_image

def test(obj):
  print(f"User Test: {obj}")
  image_path = obj.get("image_path", "https://content.pancake.vn/2-25/2025/2/15/6181ceab930d44e4303042bac938292daef10db3.jpg")
  text_prompts = obj.get("text_prompt", "object")

  print("🔹 Image Path:", image_path)

  boxes_pixel, logits, phrases, features = process_image(image_path, text_prompts, True)

  print("🔹 Bounding Boxes:", boxes_pixel)
  print("🔹 Logits:", logits)
  print("🔹 Phrases:", phrases)
  print("🔹 Feature Vectors Shape:", len(features), "x", len(features[0]) if features else 0)
  