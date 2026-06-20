import os
import time
import uuid
import requests
import json
import random
import urllib.parse
import threading
from dotenv import load_dotenv

# Load with absolute path (Part 17)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

class MultiImageGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), "assets", "ai_images")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load credentials
        self.cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "YOUR_ACCOUNT_ID")
        self.cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "YOUR_API_TOKEN")
        self.horde_api_key = os.getenv("AI_HORDE_API_KEY", "0000000000") # Default anonymous key
        self.semaphore = threading.Semaphore(1) # STRICTly sequential (Part 17)
        
        if self.cf_account_id == "YOUR_ACCOUNT_ID":
            print(f"   [WARNING] Cloudflare Account ID not loaded from {env_path}")
        else:
            print(f"   [ImageGen] Cloudflare initialized (ID: {self.cf_account_id[:5]}...)")

    def generate_image(self, scene_id: int, prompt: str, base_prompt: str = "", seed: int = None) -> str:
        """
        Main entry point for image generation with character consistency.
        """
        unique_id = uuid.uuid4().hex[:8]
        filename = f"scene_{scene_id}_{unique_id}.png"
        output_path = os.path.join(self.output_dir, filename)

        # PART 1 & 4: Character Consistency Structure
        # Combine base character prompt with scene-specific description
        if base_prompt:
            final_prompt = f"{base_prompt}, same character, sharp focus, hyper-detailed face, cinematic lighting, {prompt}, 8k, masterpiece, vibrant colors, mythological atmosphere"
        else:
            final_prompt = f"cinematic masterpiece, indian mythology, ultra-detailed digital art, epic lighting, sharp focus, 8k, {prompt}, hyper-realistic, high contrast"

        print(f"\n[ImageGen] Generating image for Scene {scene_id} (Consistency: {'ON' if base_prompt else 'OFF'})...")

        # --- Fallback Chain ---
        
        # 1. Pollinations (Reliable & Fast - Part 17.3)
        if self._try_api("Pollinations", self._call_pollinations, final_prompt, output_path, seed=seed):
            return output_path

        # 2. AI Horde (Global Crowd Fallback)
        if self._try_api("AI Horde", self._call_ai_horde, final_prompt, output_path, seed=seed):
            return output_path

        # 3. Cloudflare (Account-Limited Backup)
        if self._try_api("Cloudflare", self._call_cloudflare, final_prompt, output_path, seed=seed):
            return output_path

        # 5. Local Fail-safe (Solid Color Placeholder)
        if self._generate_placeholder(final_prompt, output_path):
            return output_path

        raise Exception(f"[ERROR] CRITICAL: All image generation APIs failed for Scene {scene_id}.")

    def _try_api(self, name, func, prompt, path, seed=None, retries=2):
        """Generic retry wrapper for API calls with jitter (Part 16)."""
        with self.semaphore:
            # Add initial jitter to prevent simultaneous bursts
            time.sleep(random.uniform(0.5, 3.0))
            
            for i in range(retries):
                try:
                    print(f"   -> Using {name} (Attempt {i+1}/{retries})...")
                    if func(prompt, path, seed=seed):
                        # VERIFY IMAGE IS VALID (Part 12)
                        from PIL import Image
                        try:
                            with Image.open(path) as img:
                                img.verify()
                            print(f"   [Done] {name} success!")
                            return True
                        except:
                            print(f"   [ImageGen] {name} returned corrupt image. Falling back...")
                            if os.path.exists(path): os.remove(path)
                except Exception as e:
                    print(f"   [Error] {name} error: {e}")
                
                if i < retries - 1:
                    time.sleep(10) # Heavy cooldown to prevent 429s (Part 17.1)
        return False

    def _generate_placeholder(self, prompt, path):
        """Final fail-safe: Generate a simple solid placeholder with subtle grain (Part 13)"""
        from PIL import Image, ImageDraw
        import random
        try:
            print(f"   [ImageGen] Generating fail-safe placeholder...")
            img = Image.new('RGB', (1080, 1920), (30, 30, 50))
            img.save(path)
            return True
        except Exception as e:
            print(f"   [Placeholder Error] {e}")
            return False

    def _call_cloudflare(self, prompt, path, seed=None):
        if self.cf_account_id == "YOUR_ACCOUNT_ID" or self.cf_token == "YOUR_API_TOKEN":
            return False
            
        headers = {"Authorization": f"Bearer {self.cf_token}"}
        # PART 17.2: Use bare prompt only (Cloudflare 400 Routing Fix)
        # Added width and height for 9:16 vertical ratio
        payload = {
            "prompt": prompt,
            "width": 576,
            "height": 1024
        }
        # Try a few models in case one is restricted (Part 17)
        models = [
            "@cf/bytedance/stable-diffusion-xl-lightning",
            "@cf/runwayml/stable-diffusion-v1-5",
            "@cf/stabilityai/stable-diffusion-xl-base-1.0"
        ]
        
        for model in models:
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/ai/run/{model}"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=40)
                # IMPORTANT: Pause after every Cloudflare attempt regardless of result
                time.sleep(5)
                
                if response.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(response.content)
                    return True
                else:
                    print(f"   [Cloudflare Model {model.split('/')[-1]} failed] Status: {response.status_code}")
            except Exception as e:
                print(f"   [Cloudflare Connection Error] {e}")
        return False

    def _call_pollinations(self, prompt, path, seed=None):
        # PART 11: Prompt cleaning (Part 17)
        safe_prompt = prompt.replace("\n", " ")[:600]
        encoded_prompt = urllib.parse.quote(safe_prompt)
        final_seed = seed if seed is not None else random.randint(1, 1000000)
        
        # Try multiple models (Part 17.3)
        p_models = ["flux-pro", "flux", "turbo"]
        for p_model in p_models:
            url = f"https://pollinations.ai/p/{encoded_prompt}?width=1080&height=1920&seed={final_seed}&model={p_model}"
            try:
                print(f"   -> Testing Pollinations model: {p_model}...")
                response = requests.get(url, timeout=40)
                ctype = response.headers.get("Content-Type", "").lower()
                
                if response.status_code == 200 and "image" in ctype:
                    with open(path, "wb") as f:
                        f.write(response.content)
                    return True
                else:
                    print(f"   [Pollinations {p_model} failed] CType: {ctype}")
            except Exception as e:
                print(f"   [Pollinations Error] {e}")
            time.sleep(2) # Prevent rapid bursts
        return False

    def _call_ai_horde(self, prompt, path, seed=None):
        submit_url = "https://stablehorde.net/api/v2/generate/async"
        headers = {"apikey": self.horde_api_key}
        payload = {
            "prompt": prompt,
            "params": {
                "sampler_name": "k_euler",
                "cfg_scale": 7.5,
                "width": 1080,
                "height": 1920,
                "steps": 20,
                "seed": seed if seed is not None else random.randint(1, 1000000)
            }
        }
        
        resp = requests.post(submit_url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 202: return False
        job_id = resp.json().get("id")
        if not job_id: return False

        status_url = f"https://stablehorde.net/api/v2/generate/check/{job_id}"
        for _ in range(90): # Increase to 3 minutes max (PART 14)
            try:
                check = requests.get(status_url, timeout=40).json()
                if check.get("done"):
                    result_url = f"https://stablehorde.net/api/v2/generate/status/{job_id}"
                    result = requests.get(result_url, timeout=40).json()
                    img_url = result.get("generations", [{}])[0].get("img")
                    if img_url:
                        img_data = requests.get(img_url, timeout=30).content
                        with open(path, "wb") as f:
                            f.write(img_data)
                        return True
                    break
            except Exception as e:
                print(f"   [AI Horde Loop Error] {e}")
            time.sleep(2)
        return False
