"""
image_generator.py — AI Image Generator for Alreetal
Multi-provider image generation with graceful fallback:
  1. Gemini image models (when not rate-limited)
  2. HuggingFace FLUX (router.huggingface.co — needs HF_TOKEN in .env)
  3. Scene-specific PIL art (always works — unique per scene based on image_prompt)

Saves results to assets/ai_images/scene_{id}.png
"""

import os
import re
import math
import time
import random
import uuid
import textwrap
import urllib.parse

import requests as req
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client  = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN", "")   # optional: add to .env for real FLUX images
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# ── Gemini image models ───────────────────────────────────────────────────────
GEMINI_IMG_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

# ── Hugging Face Image Models (FLUX & SDXL Candidates) ────────────────────────
HF_IMAGE_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "stabilityai/stable-diffusion-3.5-large",
    "runwayml/stable-diffusion-v1-5",
    "prompthero/openjourney",
]

class HFImageManager:
    def __init__(self):
        self.tokens = []
        # Support multiple tokens for higher quota
        primary = os.getenv("HF_TOKEN")
        if primary: self.tokens.append(primary)
        for i in range(1, 10):
            t = os.getenv(f"HF_TOKEN_{i}")
            if t: self.tokens.append(t)
        self.current_idx = 0
        self.last_call = 0

    def get_token(self):
        if not self.tokens: return ""
        token = self.tokens[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.tokens)
        return token

    def wait_if_needed(self):
        elapsed = time.time() - self.last_call
        if elapsed < 3: time.sleep(3 - elapsed)
        self.last_call = time.time()

_hf_manager = HFImageManager()

# ── Font loader ───────────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
]

def _load_font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ── Scene-specific palette extraction ─────────────────────────────────────────
# Maps mood/keywords → rich color themes for scene-unique art
_MOOD_COLORS = {
    "ominous":     ((10, 2, 35),   (60, 10, 80),  (180, 80, 220)),
    "epic":        ((35, 10, 5),   (110, 40, 5),  (255, 160, 30)),
    "divine":      ((5, 20, 50),   (10, 60, 130), (120, 200, 255)),
    "dark":        ((5, 5, 5),     (30, 10, 15),  (200, 50, 50)),
    "cosmic":      ((5, 0, 25),    (15, 5, 70),   (80, 160, 255)),
    "warrior":     ((30, 8, 3),    (90, 20, 5),   (255, 120, 40)),
    "golden":      ((30, 20, 0),   (100, 70, 5),  (255, 210, 50)),
    "forest":      ((5, 20, 5),    (10, 60, 20),  (80, 200, 100)),
    "celestial":   ((0, 10, 40),   (10, 40, 100), (200, 180, 255)),
    "destruction": ((40, 5, 5),    (120, 15, 5),  (255, 80, 30)),
    "default":     ((10, 5, 35),   (50, 20, 70),  (200, 150, 255)),
}

# Map mood field or keywords → theme key
_KEYWORD_MAP = {
    "fire": "epic", "flame": "epic", "battle": "warrior", "war": "warrior",
    "weapon": "warrior", "arrow": "warrior", "sword": "warrior",
    "vishnu": "divine", "brahma": "divine", "saraswati": "divine",
    "shiva": "cosmic", "kailash": "cosmic", "meditation": "celestial",
    "krishna": "golden", "arjuna": "warrior", "brahmastra": "destruction",
    "curse": "dark", "demon": "dark", "rakshasa": "dark", "asura": "dark",
    "ocean": "celestial", "cosmic": "cosmic", "universe": "cosmic",
    "divine": "divine", "god": "divine", "goddess": "divine",
    "hanuman": "golden", "ram": "golden", "sita": "golden",
    "snake": "dark", "serpent": "dark", "naga": "dark",
    "sun": "epic", "moon": "celestial", "star": "celestial",
}

# Distinct geometric patterns per scene ID (cycles 0-6, repeats after 7)
_PATTERNS = ["circles", "rays", "triangles", "diamonds", "waves", "spiral", "grid"]


def _get_theme(image_prompt: str, mood: str) -> tuple:
    """Determine color theme from mood field or keywords in image_prompt."""
    lowered = (image_prompt + " " + mood).lower()
    for keyword, theme in _KEYWORD_MAP.items():
        if keyword in lowered:
            return _MOOD_COLORS.get(theme, _MOOD_COLORS["default"])
    return _MOOD_COLORS.get(mood.lower(), _MOOD_COLORS["default"])


def _extract_subject(image_prompt: str) -> str:
    """
    Extract the main visual subject for labelling the PIL art.
    Handles both:
      - New storyboard format: 'Characters: Urmila, young princess...'
      - Old free-form prompts: keywords extracted by stop-word filter
    """
    # New storyboard format: pull from 'Characters:' field
    char_match = re.search(r"Characters:\s*([^.]+)", image_prompt, re.IGNORECASE)
    if char_match:
        # Take just the first part before any comma (the name)
        char_text = char_match.group(1).strip()
        name = char_text.split(",")[0].strip()
        # Capitalise each word, max 3 words
        words = name.split()[:3]
        return " ".join(w.title() for w in words)

    # Fallback: filter stop-words from first sentence
    stop_words = {
        "the", "a", "an", "in", "on", "at", "of", "and", "with",
        "ultra", "detailed", "cinematic", "dramatic", "lighting",
        "digital", "painting", "art", "style", "epic", "ancient",
        "indian", "mythology", "vertical", "composition", "format",
        "portrait", "rich", "jewel", "tones", "stunning", "showing",
        "movie", "frame", "animated", "film", "high", "quality",
    }
    first_sentence = image_prompt.split(".")[0]
    words = re.findall(r"[A-Za-z]+", first_sentence)
    kept  = [w for w in words if w.lower() not in stop_words][:4]
    return " ".join(kept) if kept else image_prompt[:30]


def _make_scene_image(scene_id: int, image_prompt: str, mood: str = "default") -> Image.Image:
    """
    Generate a premium blurred gradient fallback art (no text labels, no generic patterns).
    Every scene gets a unique color palette based on keywords.
    """
    W, H = 1080, 1920
    rng  = random.Random(scene_id * 137 + 42)  # deterministic per scene

    # ── Color theme ───────────────────────────────────────────────────────────
    top_col, bot_col, accent = _get_theme(image_prompt, mood)

    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Vertical gradient background
    for y in range(H):
        t = y / H
        r = int(top_col[0] + (bot_col[0] - top_col[0]) * t)
        g = int(top_col[1] + (bot_col[1] - top_col[1]) * t)
        b = int(top_col[2] + (bot_col[2] - top_col[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Premium Blurred Gradient Fallback (No text labels, no patterns) ───────
    # We use multiple horizontal/vertical light sources to fake a cinematic scene
    for _ in range(5):
        lx, ly = rng.randint(0, W), rng.randint(0, H)
        lr = rng.randint(400, 1000)
        # Create a light glow
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)
        o_draw.ellipse([lx-lr, ly-lr, lx+lr, ly+lr], 
                      fill=(accent[0], accent[1], accent[2], rng.randint(20, 50)))
        img.paste(overlay, (0, 0), overlay)
    
    return img.convert("RGB")

    return img.convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
class ImageGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), "assets", "ai_images")
        os.makedirs(self.output_dir, exist_ok=True)

    # ── Provider 1: Gemini ────────────────────────────────────────────────────
    def _try_gemini(self, scene_id: int, prompt: str, output_path: str) -> bool:
        full = (
            f"{prompt}. Ultra-detailed Indian mythology digital painting, "
            "dramatic cinematic lighting, rich jewel tones, vertical 9:16 portrait."
        )
        TRANSIENT = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")
        for model in GEMINI_IMG_MODELS:
            for attempt in range(2):
                try:
                    resp = client.models.generate_content(
                        model=model,
                        contents=full,
                        config=types.GenerateContentConfig(
                            response_modalities=["TEXT", "IMAGE"],
                        ),
                    )
                    for part in resp.candidates[0].content.parts:
                        if part.inline_data is not None:
                            with open(output_path, "wb") as f:
                                f.write(part.inline_data.data)
                            print(f"   ✅ Scene {scene_id}: Gemini AI image!")
                            return True
                    break
                except Exception as e:
                    err = str(e)
                    print(f"   ❌ Gemini Error: {err[:100]}")
                    if any(t in err for t in TRANSIENT):
                        if attempt == 0:
                            print(f"   ⏳ Gemini rate-limited. Skipping to next...")
                            break
                        else:
                            break
                    else:
                        break
        return False

    # ── Provider 1: HuggingFace FLUX (Hyper-Realism) ───────────────────────────
    def _try_huggingface(self, scene_id: int, prompt: str, output_path: str) -> bool:
        """Tries various models on HuggingFace with automatic token rotation on failure."""
        if not _hf_manager.tokens:
            return False

        # Try multiple models for maximum reliability, 3 times each
        for attempt in range(3):
            for model_id in HF_IMAGE_MODELS:
                token = _hf_manager.get_token() # Fetches next rotated token for every request
                _hf_manager.wait_if_needed()
                url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                payload = {"inputs": prompt}

                print(f"   🤗 Scene {scene_id} (Attempt {attempt+1}/3): Requesting realistic {model_id.split('/')[-1]}...")
                try:
                    r = req.post(url, json=payload, headers=headers, timeout=40)
                    ct = r.headers.get("Content-Type", "")

                    if r.status_code == 200 and "image" in ct:
                        from PIL import Image as _Img
                        import io as _io
                        img = _Img.open(_io.BytesIO(r.content)).convert("RGB")
                        # Enforce 1080x1920 Full HD
                        img = img.resize((1080, 1920), _Img.LANCZOS)
                        img.save(output_path, "PNG")
                        print(f"   ✅ Scene {scene_id}: Realistic AI image saved! ({len(r.content)//1024}KB)")
                        return True
                    elif r.status_code == 429:
                        print(f"   ⏳ Scene {scene_id}: HF rate-limited for {model_id}. Trying next...")
                        continue
                    elif r.status_code == 503:
                        # Model is loading. Check for estimated_time
                        try:
                            err_data = r.json()
                            est_time = err_data.get("estimated_time", 20)
                            print(f"   ⏳ Scene {scene_id}: {model_id} is loading. Waiting {est_time:.1f}s...")
                            time.sleep(min(est_time, 30)) # Wait max 30s per model load check
                        except:
                            time.sleep(10)
                        continue
                    elif r.status_code == 402:
                        print(f"   ⚠️ Scene {scene_id}: Token exhausted for {model_id}. Rotating...")
                        continue
                    else:
                        print(f"   ⚠️ Scene {scene_id}: {model_id} error {r.status_code} - {r.text[:100]}")
                except Exception as e:
                    print(f"   ⚠️ Scene {scene_id}: {model_id} exception - {str(e)[:100]}")
                    continue
            
            # Brief pause before retrying the entire model block
            if attempt < 2:
                print(f"   🔁 Timeout/Failure. Retrying API block in 5 seconds...")
                time.sleep(5)
                
        return False
        
    # ── Provider 3: Pexels Stock Fallback (Realistic Photos) ───────────────────
    def _try_pexels(self, scene_id: int, prompt: str, output_path: str) -> bool:
        """Searches Pexels for high-quality stock images as a reliable realistic fallback."""
        if not PEXELS_API_KEY:
            return False
            
        # Extract keywords for better search
        keywords = prompt.split(',')[0].replace("A photorealistic cinematic 8k movie frame showing", "").strip()
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(keywords)}&per_page=1&orientation=portrait"
        headers = {"Authorization": PEXELS_API_KEY}
        
        print(f"   📷 Scene {scene_id}: Searching Pexels for '{keywords}'...")
        try:
            r = req.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get("photos"):
                    img_url = data["photos"][0]["src"]["large2x"]
                    img_data = req.get(img_url, timeout=15).content
                    
                    from PIL import Image as _Img
                    import io as _io
                    img = _Img.open(_io.BytesIO(img_data)).convert("RGB")
                    img = img.resize((1080, 1920), _Img.LANCZOS)
                    img.save(output_path, "PNG")
                    print(f"   ✅ Scene {scene_id}: Realistic Stock image found!")
                    return True
        except Exception as e:
            print(f"   ⚠️ Scene {scene_id}: Pexels error - {str(e)[:50]}")
            
        return False

    # ── Provider 4: Scene-specific PIL art (last resort) ──────────────────────
    def _make_pil_art(self, scene_id: int, image_prompt: str,
                      mood: str, output_path: str) -> bool:
        try:
            img = _make_scene_image(scene_id, image_prompt, mood)
            img.save(output_path, "PNG")
            print(f"   🎨 Scene {scene_id}: Unique scene art ({_PATTERNS[scene_id % 7]} / {mood or 'default'})")
            return True
        except Exception as e:
            print(f"   ❌ Scene {scene_id}: PIL art failed: {e}")
            return False

    # ── Main entry ────────────────────────────────────────────────────────────
    def generate_image(self, scene_id: int, image_prompt: str,
                       unique_id: str, mood: str = "default") -> str | None:
        """
        Generates a 100% fresh image for every call.
        No caching, unique variation tag added to prompt.
        """
        filename = f"scene_{scene_id}_{unique_id}.png"
        output_path = os.path.join(self.output_dir, filename)

        # Force a real scene with a unique variation tag and premium suffix
        enhanced_prompt = (
            f"{image_prompt}. Generate a real scene, not abstract, not background. "
            f"highly detailed, cinematic, 4k, masterpiece, no abstract background, no plain colors. "
            f"unique variation {unique_id}"
        )

        # Try provider chain – ONLY Hugging Face for realism
        if self._try_huggingface(scene_id, enhanced_prompt, output_path):
            return output_path
            
        # If HF fails, raise an error to stop execution as requested (no fallbacks)
        raise RuntimeError(f"CRITICAL: Scene {scene_id} image generation failed via Hugging Face. Stopping execution.")

    def generate_all(self, script_data: list, unique_id: str, clear_cache: bool = True) -> dict:
        print(f"\n🎨 Starting Fresh Image Generation for {len(script_data)} scenes (ID: {unique_id})...\n")
        images = {}

    def generate_all(self, script_data: list, clear_cache: bool = True) -> dict:
        print(f"\n🎨 Starting Image Generation for {len(script_data)} scenes...\n")
        images = {}

        if clear_cache:
            for f in os.listdir(self.output_dir):
                if f.startswith("scene_") and f.endswith(".png"):
                    try:
                        os.remove(os.path.join(self.output_dir, f))
                    except:
                        pass
            print("   🧹 Cleared old image cache for fresh generation.")

        for scene in script_data:
            scene_id    = scene["id"]
            img_prompt  = scene.get("image_prompt", f"Ancient Indian mythology scene {scene_id}")
            mood        = scene.get("mood", "default")

            path = self.generate_image(scene_id, img_prompt, unique_id, mood)
            images[scene_id] = path
            time.sleep(0.5)

        success = sum(1 for p in images.values() if p)
        print(f"\n🎨 Image generation done: {success}/{len(script_data)} scenes ready.\n")
        return images


# --- TESTING ---
if __name__ == "__main__":
    # Test PIL art for variety
    test_scenes = [
        {"id": 1, "image_prompt": "Lord Vishnu reclining on Shesha cosmic ocean divine light", "mood": "divine"},
        {"id": 2, "image_prompt": "Lord Shiva meditating Mount Kailash cosmic storm", "mood": "cosmic"},
        {"id": 3, "image_prompt": "Arjuna warrior archer battlefield Kurukshetra", "mood": "warrior"},
        {"id": 4, "image_prompt": "Brahmastra weapon celestial arrow destruction", "mood": "destruction"},
    ]
    gen = ImageGenerator()
    results = gen.generate_all(test_scenes)
    print("Results:", results)
