"""
thumbnail_gen.py — Automated Thumbnail Engine for Alreetal AI Shorts
Generates a cinematic base image and overlays high-impact bold text.
Part 7: "BIGGEST MISTAKE", "HIDDEN TRUTH" style.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from engine.image_gen import ImageDepthDualGenerator

# Cinematic Thumbnail Prompts
THUMBNAIL_PROMPT_PREFIX = "cinematic close-up, intense emotion, dramatic lighting, indian mythology, ultra realistic, 4k, dark background, centered composition, thumbnail style: "

class ThumbnailGenerator:
    def __init__(self):
        self.generator = ImageDepthDualGenerator()
        self.font_path = "C:/Windows/Fonts/arialbd.ttf"
        if not os.path.exists(self.font_path):
            self.font_path = "C:/Windows/Fonts/arial.ttf"

    def generate_thumbnail(self, topic: str, text_overlay: str, output_path: str):
        """
        1. Generate AI image
        2. Overlay Bold Yellow/White text with Black outline
        """
        print(f"\n[Thumbnail] Generating cinematic thumbnail for: {topic}...")
        
        prompt = f"{THUMBNAIL_PROMPT_PREFIX}{topic}"
        
        # We use the existing dual_gen but we want a horizontal aspect for Full Video thumbnails
        # Most of our APIs default to Square or Vertical. We will request square and crop if needed,
        # or just use the generated image and center the text.
        img_path, _ = self.generator.generate_scene_assets("thumbnail", prompt, "thumb_run")
        
        if not img_path or not os.path.exists(img_path):
            print("   [Thumbnail Error] Image generation failed.")
            return None

        # Process with Pillow
        try:
            with Image.open(img_path) as img:
                # Convert to RGB if needed
                img = img.convert("RGB")
                w, h = img.size
                draw = ImageDraw.Draw(img)
                
                # Part 7 Rules: 2-3 words only, Bold font, Yellow/White text, Black outline
                font_size = int(h * 0.15) # Dynamic sizing
                try:
                    font = ImageFont.truetype(self.font_path, font_size)
                except:
                    font = ImageFont.load_default()

                text = text_overlay.upper()
                bbox = draw.textbbox((0, 0), text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                
                # Position: Centered bottom-half
                tx = (w - tw) // 2
                ty = h - th - int(h * 0.1)
                
                # Draw thick black outline
                offset = 6
                for ox in range(-offset, offset+1):
                    for oy in range(-offset, offset+1):
                        draw.text((tx+ox, ty+oy), text, font=font, fill="black")
                
                # Draw main text (Yellow)
                draw.text((tx, ty), text, font=font, fill="yellow")
                
                img.save(output_path, "JPEG", quality=95)
                print(f"   [Thumbnail Success] Saved to: {output_path}")
                return output_path
                
        except Exception as e:
            print(f"   [Thumbnail Error] Text overlay failed: {e}")
            return img_path
