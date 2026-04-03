import os
import requests
import time
import json
from dotenv import load_dotenv

load_dotenv()

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
BASE_DIR = os.path.join("app", "static", "themes")

IMAGE_COUNT = int(os.getenv("PIXABAY_IMAGE_COUNT", "50"))

themes_json = os.getenv("PIXABAY_THEMES", "")
if themes_json:
    THEMES = json.loads(themes_json)
else:
    THEMES = {
        "General": "celebration party",
        "Farewell": "bye celebration party ciao cheers farewell goodbye"
    }

def download_images():
    os.makedirs(BASE_DIR, exist_ok=True)
    
    for theme_name, query in THEMES.items():
        theme_dir = os.path.join(BASE_DIR, theme_name)
        os.makedirs(theme_dir, exist_ok=True)
        
        print(f"Downloading images for {theme_name}...")
        url = "https://pixabay.com/api/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "image_type": "photo",
            "per_page": IMAGE_COUNT,
            "orientation": "horizontal"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        hits = data.get("hits", [])
        for i, hit in enumerate(hits[:IMAGE_COUNT]):
            img_url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not img_url:
                continue
                
            img_data = requests.get(img_url).content
            file_path = os.path.join(theme_dir, f"{i+1}.jpg")
            with open(file_path, "wb") as f:
                f.write(img_data)
                
        # To avoid hitting rate limits too fast
        time.sleep(1)

if __name__ == "__main__":
    download_images()
    print("Done downloading!")
