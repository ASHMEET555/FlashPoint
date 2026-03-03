import os
import requests
from dotenv import load_dotenv

# Load API key from .env
load_dotenv(override=True)
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("❌ ERROR: OPENROUTER_API_KEY is missing from .env")
    exit(1)

print("⏳ Fetching available models from OpenRouter...\n")

headers = {
    "Authorization": f"Bearer {api_key}"
}

try:
    response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
    response.raise_for_status()
    
    models = response.json().get("data", [])
    
    print("--- 🟢 AVAILABLE FREE MODELS ---")
    free_count = 0
    
    for model in models:
        # OpenRouter pricing is usually a string like "0", "0.0", or a very small float
        pricing = model.get("pricing", {})
        prompt_price = float(pricing.get("prompt", -1))
        completion_price = float(pricing.get("completion", -1))
        
        # Check if both prompt and completion are effectively free
        if prompt_price == 0.0 and completion_price == 0.0:
            print(f"- {model['id']}")
            free_count += 1
            
    print(f"\nTotal free models found: {free_count}")
    print("--------------------------------")
    
except Exception as e:
    print(f"❌ Failed to fetch models: {e}")