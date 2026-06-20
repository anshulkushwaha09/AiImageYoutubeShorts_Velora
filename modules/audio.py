import os
import asyncio
import edge_tts
from mutagen.mp3 import MP3

class AudioEngine:
    def __init__(self, voice="hi-IN-MadhurNeural"):
        self.voice = voice
        self.output_dir = os.path.join(os.getcwd(), "assets", "audio_clips")
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_audio(self, text, output_filename, retries=3):
        """
        Generates MP3 and captures WordBoundary timestamps for precision sync.
        Returns (output_path, word_offsets)
        """
        output_path = os.path.join(self.output_dir, output_filename)
        word_offsets = []
        
        for attempt in range(retries):
            try:
                # Phase 26: 1.20x speed for professional storytelling (+20%)
                communicate = edge_tts.Communicate(text, self.voice, rate="+20%")
                
                # We use stream() to catch WordBoundary events
                with open(output_path, "wb") as f:
                    async for event in communicate.stream():
                        if event["type"] == "audio":
                            f.write(event["data"])
                        elif event["type"] == "WordBoundary":
                            # 'offset' is in 100ns ticks. Convert to seconds.
                            # 'duration' is also in 100ns ticks.
                            word_offsets.append({
                                "text": event["text"],
                                "start": event["offset"] / 10000000,
                                "duration": event["duration"] / 10000000
                            })
                
                # fallback if no WordBoundary events were found
                if not word_offsets:
                    words = text.split()
                    if words:
                        # Estimate total duration (get it from file later if needed, 
                        # but for now we'll wait for the loop to finish)
                        # Actually, better to do this in process_script after duration is known.
                        pass
                
                return output_path, word_offsets
            
            except Exception as e:
                print(f"      [Audio Warning] (Attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    print("      [Audio Error] Failed to generate audio after max retries.")
                    raise e

    def get_audio_duration(self, file_path):
        try:
            audio = MP3(file_path)
            return audio.info.length
        except Exception as e:
            print(f"[Audio Error] Error reading audio length: {e}")
            return 0.0

    async def process_script(self, script_data):
        print(f"[Audio] Starting Audio Generation for {len(script_data)} scenes...")
        
        for scene in script_data:
            scene_id = scene['id']
            # Prioritize narration (new schema) then text, then scene_text for voiceover
            text = scene.get('narration', scene.get('text', scene.get('scene_text', '')))
            filename = f"voice_{scene_id}.mp3"
            
            try:
                # Generate Audio and get word timestamps
                file_path, word_offsets = await self.generate_audio(text, filename)
                
                # Get Duration
                duration = self.get_audio_duration(file_path)
                
                # Heuristic: If API failed to provide WordBoundaries, split manually by duration
                if not word_offsets:
                    words = text.split()
                    if words:
                        avg_dur = duration / len(words)
                        word_offsets = [
                            {"text": w, "start": i * avg_dur, "duration": avg_dur}
                            for i, w in enumerate(words)
                        ]
                
                scene['audio_path'] = file_path
                scene['duration'] = duration
                scene['word_offsets'] = word_offsets
                
                print(f"   [Audio Done] Scene {scene_id}: {duration:.2f}s generated ({len(word_offsets)} words synced).")
                
                # CRITICAL: Sleep for 1 second to be polite to the API
                # This prevents the "Connection Timeout" error
                await asyncio.sleep(1) 
                
            except Exception as e:
                print(f"   [Audio Warning] Audio failed for Scene {scene_id}: {e}. Using 1s silence fallback.")
                # Fallback to an empty/silent state instead of skipping the whole scene
                scene['audio_path'] = None 
                scene['duration'] = 2.0 # Default 2s for images without audio
                continue
            
        return script_data