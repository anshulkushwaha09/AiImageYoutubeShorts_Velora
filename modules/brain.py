import os
import json
import time
from google import genai
from dotenv import load_dotenv

# Load API Key from .env
load_dotenv()

def get_all_gemini_keys():
    keys = []
    base = os.getenv("GEMINI_API_KEY")
    if base and len(base) > 10 and not base.startswith("AQ."):
        keys.append(base)
    for k, v in os.environ.items():
        if k.startswith("GEMINI_API_KEY_") and v and len(v) > 10 and not v.startswith("AQ.") and v not in keys:
            keys.append(v)
    return keys

GEMINI_KEYS = get_all_gemini_keys()

# Model priority: try lightest quota first, escalate if needed
# All names confirmed via client.models.list()
MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-1.5-flash-latest"]

def _call_gemini(prompt: str, retries: int = 3, wait: int = 20) -> str:
    """
    Calls Gemini with automatic retry + model fallback + API KEY fallback.
    Handles: 429 RESOURCE_EXHAUSTED, 503 UNAVAILABLE, 403 PERMISSION_DENIED.
    Returns the response text.
    """
    if not GEMINI_KEYS:
        raise ValueError("No valid Gemini API keys found. Ensure keys start with AIzaSy.")

    TRANSIENT = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")
    KEY_ERRORS = ("403", "PERMISSION_DENIED", "400", "API_KEY_INVALID", "INVALID_ARGUMENT")
    
    for api_key in GEMINI_KEYS:
        print(f"   [Brain] Trying API Key starting with: {api_key[:8]}...")
        client = genai.Client(api_key=api_key)
        key_is_bad = False
        
        for model in MODELS:
            if key_is_bad: break
            
            for attempt in range(retries):
                try:
                    response = client.models.generate_content(model=model, contents=prompt)
                    return response.text
                except Exception as e:
                    err = str(e)
                    if any(t in err for t in KEY_ERRORS):
                        print(f"   [Brain Warning] API Key rejected. Switching to next key...")
                        key_is_bad = True
                        break
                    elif any(t in err for t in TRANSIENT):
                        if attempt < retries - 1:
                            print(f"   --- Transient error on {model}. Waiting {wait}s... (attempt {attempt+1}/{retries})")
                            time.sleep(wait)
                        else:
                            print(f"   [Warning] Quota exceeded on {model}. Trying next model...")
                            break
                    else:
                        print(f"   [Warning] Unknown error: {err[:50]}. Skipping model...")
                        break
    
    raise RuntimeError("All Gemini API keys and models failed.")
    


def _get_fallback_script():
    """Returns a high-quality pre-defined script if Gemini fails."""
    return [
        {
            "id": 1,
            "narration": "कुरुक्षेत्र के युद्ध मैदान में एक सोलह साल का वीर अकेला खड़ा था—अभिमन्यु।",
            "english_caption": "THE YOUNG WARRIOR!",
            "image_prompt": "Epic cinematic realistic style. A teenage Indian warrior Abhimanyu, royal golden armor, blue dhoti, holding a massive golden bow, standing in the center of a chaotic battlefield Kurukshetra. Thousands of soldiers and chariots in background. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 2,
            "narration": "द्रोणाचार्य ने एक अभेद्य चक्रव्यूह बनाया था, जिसे भेदना नामुमकिन था।",
            "english_caption": "THE IMPENETRABLE CIRCLE",
            "image_prompt": "Epic cinematic realistic style. A top-down bird's eye view of the Chakravyuha formation: millions of soldiers arranged in a massive complex spiral pattern on a dusty plain. In the center, a golden light. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 3,
            "narration": "अभिमन्यु ने अपनी मां के गर्भ में ही इसे तोड़ने का रहस्य सुना था।",
            "english_caption": "A MYSTERY BORN...",
            "image_prompt": "Epic cinematic realistic style. Close-up of a pregnant Indian queen Subhadra sitting on a carved balcony, moonlit night. Nearby, Arjuna is explaining battle tactics with animated hand gestures. Soft glowing lanterns. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 4,
            "narration": "बिना डरे, वह अपने रथ को लेकर दुश्मन की सेना के बीच कूद पड़ा।",
            "english_caption": "CHARGE INTO DARKNESS!",
            "image_prompt": "Epic cinematic realistic style. Low angle dynamic shot of Abhimanyu's golden chariot charging into a wall of enemy spears. Dust flying, horses galloping furiously, intense sunlight. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 5,
            "narration": "एक-एक करके उसने सात परतों को तोड़ दिया, लेकिन अंत में वह घिर गया।",
            "english_caption": "TRAPPED IN THE CORE",
            "image_prompt": "Epic cinematic realistic style. Abhimanyu surrounded by seven powerful warriors (Maharathis) including Drona and Karna. He is holding a broken chariot wheel as a shield, standing on broken wood and arrows. low angle cinematic shot. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 6,
            "narration": "सात महारथियों ने मिलकर उस निहत्थे बालक पर वार किया।",
            "english_caption": "7 AGAINST 1",
            "image_prompt": "Epic cinematic realistic style. Dramatic silhouettes of seven warriors attacking a central figure under a dark bloody sky of Kurukshetra. Shafts of divine golden light piercing the dust. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 7,
            "narration": "उसका बलिदान आज भी वीरता की सबसे बड़ी मिसाल माना जाता है।",
            "english_caption": "IMMORTAL SACRIFICE",
            "image_prompt": "Epic cinematic realistic style. The spirit of a young warrior rising from the battlefield towards a glowing celestial portal in the clouds. Thousands of glowing arrows on the ground. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 8,
            "narration": "क्या आप अभिमन्यु की इस महान गाथा को जानते थे? सब्सक्राइब करें!",
            "english_caption": "A HERO'S LEGEND!",
            "image_prompt": "Epic cinematic realistic style. A panoramic wide shot of the Kurukshetra dawn, golden sun rising over a field of broken weapons and historical remains. Cinematic lens flare. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        }
    ]


class ContentBrain:
    def get_trending_topic(self):
        """
        Picks a viral Sanatan Dharma/Ancient India topic for the channel.
        Maintains a memory log to prevent repeats.
        """
        import os
        log_file = "used_topics.txt"
        used_topics_text = ""
        
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    # Get the last 15 topics to avoid blowing up the context window over time
                    lines = f.readlines()
                    last_topics = [line.strip() for line in lines if line.strip()][-15:]
                    if last_topics:
                        used_topics_text = "CRITICAL RULE - DO NOT GENERATE THESE TOPICS (We already covered them):\n- " + "\n- ".join(last_topics)
            except Exception:
                pass

        prompt = f"""
        You are a YouTube Shorts strategist for a highly viral Indian channel focused on 
        "Untold Sanatan Dharma, Vedic Secrets, and Ancient Indian History Mysteries".
        Pick ONE specific event, mystery, powerful weapon, or lost technology from the Ramayana, Mahabharata, Puranas, or Ancient Indian History.
        
        Focus on things like: Advanced Vimanas, the Kailasa Temple mystery, untold stories of Lord Shiva, Ashwatthama's survival, curses of the Rishis, or lost Vedic science.

        {used_topics_text}

        Return ONLY the topic title. No explanation. No punctuation at the end.
        Examples:
        - "The Mystery of the Kailasa Temple"
        - "Was the Brahmastra a Nuclear Weapon?"
        - "The Untold Story of Ravana's Vimana"
        - "The Secret of the 9 Unknown Men of Ashoka"
        - "The Chilling Truth About the Bhangarh Fort"
        - "What Really Happened to the Saraswati River?"
        """
        try:
            topic = _call_gemini(prompt)
        except Exception as e:
            print(f"   [Brain Error] Could not fetch trending topic: {e}. Using default topic.")
            topic = None

        if not topic or "id" in topic or "narration" in topic:
            topic = "The Secret of the Kailasa Temple"
        
        topic = topic.strip().replace('"', '')
        print(f"[Brain] Selected Topic: {topic}")
        
        # Save to memory log
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(topic + "\n")
        except Exception as e:
            print(f"   [Brain Error] Could not save to memory log: {e}")
            
        return topic

    def generate_dual_scripts(self, topic: str):
        """
        Generates two distinct scripts for the same topic with Character Consistency.
        1. SHORT (20-35s, Viral Hook-based)
        2. FULL (3-4min, Structured Storytelling)
        """
        print(f"\n[Brain] Generating Dual Scripts for: {topic}...")
        
        prompt = f"""
        Generate a viral YouTube Shorts script and a full-length script about: "{topic}"
        
        Return EXACTLY this JSON structure:
        {{
            "character_base_prompt": "Description of the main character to be reused in all scenes",
            "short": [
                {{
                    "id": 1, 
                    "narration": "Hinglish storytelling narration", 
                    "english_caption": "English subtitle", 
                    "image_prompt": "Scene specific description added to base prompt. MUST include key artifacts like 'Golden Bow', 'Sudharshan Chakra', or 'Gada' if relevant to the scene.",
                    "duration": 3.0,
                    "type": "hook/build/twist/climax/cliffhanger"
                }}
            ],
            "full": [
                {{"id": 1, "narration": "Deep Hinglish narration", "english_caption": "English subtitle", "image_prompt": "cinematic prompt", "duration": 8.0}}
            ]
        }}

        SHORT RULES (YouTube Shorts ~60 seconds):
        - Style: High-retention emotional Hinglish storytelling.
        - Word Count: The TOTAL narration across all scenes must be EXACTLY 130 to 150 words (this guarantees a 60-second video).
        - Scenes: EXACTLY 12 to 15 scenes. Each scene's narration MUST be very short (around 10-12 words). This forces the visuals to change every 4-5 seconds to keep the audience hooked.
        - Structure: 
            1. HOOK (first 2 scenes): Start with a mind-blowing, impossible question or a shocking statement to immediately trap the viewer.
            2. BUILD (next 8-10 scenes): Fast-paced, high-tension mystery revealing the story piece by piece.
            3. TWIST (1 scene): A shocking revelation or "Did you know?" moment.
            4. CLIMAX (1 scene): The most epic and intense part of the story.
            5. OUTRO (final scene): A strong call to action or cliffhanger question to drive comments.
        
        CHARACTER CONSISTENCY (CRITICAL):
        1. Generate ONE `character_base_prompt` that describes the main character (e.g., "Ancient Indian warrior, long white beard, glowing eyes, divine golden armor").
        2. For each scene's `image_prompt`, provide ONLY the scene-specific details (e.g., "standing on a cliff during a storm", "holding a broken sword").
        3. Do NOT repeat the base character description in the scene prompts.
        
        IMAGE PROMPT STYLE:
        "cinematic masterpiece, ultra-detailed digital art, 8k resolution, volumetric lighting, epic atmosphere, sharp focus, vibrant mythological colors, high contrast, depth of field".
        - ENFORCE: If a weapon (like a Golden Bow) is mentioned in narration, it MUST be the focus of the image_prompt.

        Return ONLY valid JSON.
        """
        
        try:
            raw_text = _call_gemini(prompt) # Use the existing _call_gemini helper
            if not raw_text:
                print("   [Brain Error] Dual script generation failed: No response from Gemini. Falling back to pre-defined script.")
                fallback = _get_fallback_script()
                return fallback, fallback
            
            # Simple cleaning for common JSON output errors
            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_text)
            return data.get("short", []), data.get("full", [])
        except Exception as e:
            print(f"   [Brain Error] Dual script generation failed: {e}. Falling back to pre-defined script.")
            fallback = _get_fallback_script()
            return fallback, fallback

    def generate_script(self, topic: str, duration_sec: int = 60) -> list:
        # Legacy single-script method (keep for backward compatibility)
        short, full = self.generate_dual_scripts(topic)
        return full if duration_sec > 60 else short


# --- TESTING THE MODULE ---
if __name__ == "__main__":
    brain = ContentBrain()
    topic = brain.get_trending_topic()
    script = brain.generate_script(topic)

    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(script, f, indent=4, ensure_ascii=False)
        print("\u2705 Script saved to script.json")