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
                            print(f"   [Warning] Quota/Rate limit exceeded on {model}. Switching to next API key...")
                            key_is_bad = True
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
            "narration": "Kurukshetra ke yuddh maidan mein ek solah saal ka veer akela khada tha—Abhimanyu.",
            "english_caption": "THE YOUNG WARRIOR!",
            "image_prompt": "Epic cinematic realistic style. A teenage Indian warrior Abhimanyu, royal golden armor, blue dhoti, holding a massive golden bow, standing in the center of a chaotic battlefield Kurukshetra. Thousands of soldiers and chariots in background. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 2,
            "narration": "Dronacharya ne ek abhedya Chakravyuha banaya tha, jise bhedna namumkin tha.",
            "english_caption": "THE IMPENETRABLE CIRCLE",
            "image_prompt": "Epic cinematic realistic style. A top-down bird's eye view of the Chakravyuha formation: millions of soldiers arranged in a massive complex spiral pattern on a dusty plain. In the center, a golden light. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 3,
            "narration": "Abhimanyu ne apni maa ke garbh mein hi ise todne ka rahasya suna tha.",
            "english_caption": "A MYSTERY BORN...",
            "image_prompt": "Epic cinematic realistic style. Close-up of a pregnant Indian queen Subhadra sitting on a carved balcony, moonlit night. Nearby, Arjuna is explaining battle tactics with animated hand gestures. Soft glowing lanterns. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 4,
            "narration": "Bina dare, woh apne rath ko lekar dushman ki sena ke beech kood pada.",
            "english_caption": "CHARGE INTO DARKNESS!",
            "image_prompt": "Epic cinematic realistic style. Low angle dynamic shot of Abhimanyu's golden chariot charging into a wall of enemy spears. Dust flying, horses galloping furiously, intense sunlight. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 5,
            "narration": "Ek-ek karke usne saat paraton ko tod diya, lekin ant mein woh ghir gaya.",
            "english_caption": "TRAPPED IN THE CORE",
            "image_prompt": "Epic cinematic realistic style. Abhimanyu surrounded by seven powerful warriors (Maharathis) including Drona and Karna. He is holding a broken chariot wheel as a shield, standing on broken wood and arrows. low angle cinematic shot. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 6,
            "narration": "Saat maharathiyon ne milkar us nihatthe baalak par vaar kiya.",
            "english_caption": "7 AGAINST 1",
            "image_prompt": "Epic cinematic realistic style. Dramatic silhouettes of seven warriors attacking a central figure under a dark bloody sky of Kurukshetra. Shafts of divine golden light piercing the dust. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 7,
            "narration": "Uska balidan aaj bhi veerta ki sabse badi misaal maana jaata hai.",
            "english_caption": "IMMORTAL SACRIFICE",
            "image_prompt": "Epic cinematic realistic style. The spirit of a young warrior rising from the battlefield towards a glowing celestial portal in the clouds. Thousands of glowing arrows on the ground. high quality, ultra detailed, 4k, cinematic lighting, masterpiece, no abstract background, no plain colors"
        },
        {
            "id": 8,
            "narration": "Kya aap Abhimanyu ki is mahaan gaatha ko jaante the? Subscribe karein!",
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
        import random
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

        sub_topics = [
            "Advanced Vimanas and ancient flight technology described in Vaimanika Shastra",
            "The mysteries of the Kailasa Temple and how it was carved top-down from a single rock",
            "The curse of Gandhari on Lord Krishna and the end of the Yadava dynasty",
            "The legendary floating stones of Ram Setu and ancient engineering",
            "The mysterious 9 Unknown Men created by Emperor Ashoka",
            "The advanced nuclear-like weapons of Kurukshetra like the Brahmashira Astra",
            "The secret doors and underground vaults of Padmanabhaswamy Temple",
            "The science of Sanatan Dharma: Vedic mathematics, astronomy, and ancient metallurgy",
            "The untold story of Barbarik: The warrior who could end the Mahabharata in one second",
            "The mystery of the Sun Temple of Konark and its magnetic chariot wheels",
            "The lost city of Dwarka submerged under the Arabian Sea",
            "The mysterious timeline and longevity of Mahavatar Babaji",
            "The divine architecture of the Brihadeeswarar Temple's shadowless dome",
            "The story of Sage Vishwamitra creating a parallel heaven (Trishanku Swarga)",
            "The untold mystery of the King of Shambhala and Kalki's birth place",
            "The cosmic dance of Shiva (Nataraja) matching modern particle physics concepts",
            "The advanced medical science of Sushruta, the ancient father of plastic surgery",
            "The science of sound and frequency behind Vedic chants and Mantras",
            "The mystery of the Iron Pillar of Delhi which never rusts after 1600 years",
            "The legendary flight of Hanuman to fetch the Sanjeevani herb and its medical science",
            "The divine protective energy shields described in ancient Atharvaveda"
        ]
        chosen_concept = random.choice(sub_topics)

        prompt = f"""
        You are a YouTube Shorts strategist for a highly viral Indian channel focused on 
        "Untold Sanatan Dharma, Vedic Secrets, and Ancient Indian History Mysteries".
        
        Generate ONE highly viral, specific topic title about: "{chosen_concept}"
        
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
                    "narration": "Hinglish storytelling narration (Hindi language written ONLY in Latin/English alphabet, e.g. 'Kya aap jaante hain' - DO NOT use Devanagari/Hindi letters)", 
                    "english_caption": "English subtitle", 
                    "image_prompt": "Scene specific description added to base prompt. MUST include key artifacts like 'Golden Bow', 'Sudharshan Chakra', or 'Gada' if relevant to the scene.",
                    "duration": 2.5,
                    "type": "hook/build/twist/climax/cliffhanger"
                }}
            ],
            "full": [
                {{"id": 1, "narration": "Deep Hinglish narration (Hindi in Latin script)", "english_caption": "English subtitle", "image_prompt": "cinematic prompt", "duration": 6.0}}
            ]
        }}

        SHORT RULES (YouTube Shorts ~50-60 seconds):
        - Style: High-retention emotional Hinglish storytelling (Hindi language written strictly in English/Latin letters, e.g., 'Kya aap jaante hain'). Do NOT output Devanagari characters.
        - Word Count: The TOTAL narration across all scenes must be around 110 to 130 words.
        - Scenes: EXACTLY 12 to 15 scenes. Each scene's narration MUST be around 8 to 10 words. This is crucial so that the visuals change every 3 to 4 seconds, keeping the audience's eyes glued to the screen.
        - Structure: 
            1. HOOK (first 2 scenes): Start with a mind-blowing, impossible question or a shocking statement to immediately trap the viewer.
            2. BUILD (next 8-10 scenes): Fast-paced, high-tension mystery revealing the story piece by piece.
            3. TWIST (1 scene): A shocking revelation or "Did you know?" moment.
            4. CLIMAX (1 scene): The most epic and intense part of the story.
            5. OUTRO (final scene): MUST be a high-friction, comment-triggering call to action (e.g. "Write 'Mahadev' in the comments if you believe in his power", "Comment which weapon is stronger: Karna's arrow or Arjuna's bow", or "Write your answer in the comments to receive blessings"). This comment loop drives the algorithm.
        
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
                return fallback, fallback, "The Heroic Sacrifice of Abhimanyu"
            
            # Simple cleaning for common JSON output errors
            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_text)
            return data.get("short", []), data.get("full", []), topic
        except Exception as e:
            print(f"   [Brain Error] Dual script generation failed: {e}. Falling back to pre-defined script.")
            fallback = _get_fallback_script()
            return fallback, fallback, "The Heroic Sacrifice of Abhimanyu"

    def generate_viral_metadata(self, topic: str, script_data: list = None):
        """
        Generates highly clickbait/viral titles, descriptions, and thumbnail hook text for YouTube.
        Returns a dict: {"title": "...", "description": "...", "thumbnail_hook": "..."}
        """
        print(f"\n[Brain] Generating Viral Metadata for: {topic}...")
        
        script_text = ""
        if script_data:
            narrations = []
            for scene in script_data:
                narr = scene.get('narration', scene.get('text', scene.get('scene_text', '')))
                if narr:
                    narrations.append(f"- Scene {scene.get('id')}: {narr}")
            script_text = "\nHere is the exact video script narration for context:\n" + "\n".join(narrations)
            
        prompt = f"""
        You are a YouTube viral growth expert. Generate a highly clickable, emotional, curiosity-inducing YouTube Title, a search-optimized Description, and a 2-3 word high-impact THUMBNAIL Hook text for a video about: "{topic}"
        {script_text}
        
        The video is an AI-generated, high-impact storytelling video about Indian mythology/ancient mysteries.

        TITLE RULES:
        1. Must be under 100 characters.
        2. Must use curiosity gap, emotional hook, or a bold question (e.g. "The 5000-Year-Old Temple That Defies Physics! 😲", "Why Did Lord Shiva Curse His Own Son? 🤯").
        3. Include 1-2 highly relevant emojis.
        4. Must end with "#shorts" or "#shortsfeed" (in lowercase).

        DESCRIPTION RULES:
        1. Write a highly detailed description summarizing the specific story narrated in the script above. Outline the key mysteries and events.
        2. Call to action asking users to subscribe and comment.
        3. Add a section of relevant hashtags (e.g., #mythology #ancientindia #history #sanatandharma #mysteries).

        THUMBNAIL HOOK RULES:
        1. EXACTLY 2 to 3 words.
        2. Must be highly dramatic, shocking, or mysterious in all-caps (e.g. "LOST TECH", "NEVER BORN", "SHIVAS WRATH", "BIG MYSTERY", "HIDDEN TRUTH").
        3. Do NOT include emojis or punctuation.

        Return EXACTLY this JSON structure:
        {{
            "title": "Generated Viral Title",
            "description": "Generated Viral Description",
            "thumbnail_hook": "Generated 2-3 word hook in all-caps"
        }}

        Return ONLY valid JSON.
        """
        try:
            raw_text = _call_gemini(prompt)
            clean_text = raw_text.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_text)
            return {
                "title": data.get("title", f"{topic} | Untold Mystery Explained! 😲🔥 #shorts"),
                "description": data.get("description", f"Dive deep into the shocking truth about {topic}! 🤯 Watch this cinematic AI-generated story to uncover ancient mysteries.\n\n#Mythology #History #AI #SanatanDharma #AncientIndia #Trending #Shorts"),
                "thumbnail_hook": data.get("thumbnail_hook", "HIDDEN TRUTH")
            }
        except Exception as e:
            print(f"   [Brain Error] Viral metadata generation failed: {e}. Using fallback.")
            return {
                "title": f"{topic} | Untold Mystery Explained! 😲🔥 #shorts",
                "description": f"Dive deep into the shocking truth about {topic}! 🤯 Watch this cinematic AI-generated story to uncover ancient mysteries.\n\n#Mythology #History #AI #SanatanDharma #AncientIndia #Trending #Shorts",
                "thumbnail_hook": "HIDDEN TRUTH"
            }

    def generate_script(self, topic: str, duration_sec: int = 60) -> list:
        # Legacy single-script method (keep for backward compatibility)
        res = self.generate_dual_scripts(topic)
        if len(res) == 3:
            short, full, _ = res
        else:
            short, full = res
        return full if duration_sec > 60 else short


# --- TESTING THE MODULE ---
if __name__ == "__main__":
    brain = ContentBrain()
    topic = brain.get_trending_topic()
    script = brain.generate_script(topic)

    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(script, f, indent=4, ensure_ascii=False)
        print("\u2705 Script saved to script.json")