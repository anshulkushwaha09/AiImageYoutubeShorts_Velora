"""
pipeline.py — End-to-End Orchestrator for Alreetal AI Shorts
Manages Short (30s) + Full (3min) + Thumbnail generation.
Part 8, 9, 10, 11 of the Complete Automated Content Pipeline.
"""

import os
import uuid
import shutil
import asyncio
import random

from modules.brain import ContentBrain
from modules.audio import AudioEngine
from modules.composer import Composer
from modules.thumbnail_gen import ThumbnailGenerator
from engine.image_gen import ImageDepthDualGenerator

class ContentPipeline:
    def __init__(self):
        self.brain = ContentBrain()
        self.audio_engine = AudioEngine()
        self.composer = Composer()
        self.thumbnail_gen = ThumbnailGenerator()
        self.asset_gen = ImageDepthDualGenerator()
        
        self.base_output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(self.base_output_dir, exist_ok=True)

    async def generate_full_pipeline(self, topic: str):
        """
        Complete Automated Generation:
        1. Generate Short and Full scripts via Brain
        2. Generate Audio & Synchronized WordBoundaries
        3. Generate Visual Assets (Images & Depth for Full/Short)
        4. Compose Final Video Clips
        5. Generate cinematic Thumbnail with text
        """
        run_id = f"video_{uuid.uuid4().hex[:8]}"
        run_path = os.path.join(self.base_output_dir, run_id)
        short_path = os.path.join(run_path, "short")
        full_path = os.path.join(run_path, "full")
        
        os.makedirs(short_path, exist_ok=True)
        os.makedirs(full_path, exist_ok=True)
        
        print(f"\n[PIPELINE] STARTING COMPLETE PIPELINE: {topic} (ID: {run_id})")

        # PART 1: SCRIPTING
        print("   [Brain] Generating dual-scripts (Short + Full)...")
        res = self.brain.generate_dual_scripts(topic)
        if len(res) == 3:
            short_script, full_script, actual_topic = res
        else:
            short_script, full_script = res
            actual_topic = topic
        
        if not short_script or not full_script:
            print("   [Error] Script generation failed.")
            return

        # PART 2 & 3: SHORT GENERATION
        print("   [1/3] Skipping Short Video...")
        # short_video = await self.process_video_type(short_script, short_path, "short.mp4", run_id)
        short_video = "skipped"
        
        # PART 4 & 5: FULL VIDEO GENERATION
        print("   [2/3] Generating Full Video (3-4 min)...")
        full_video = await self.process_video_type(full_script, full_path, "full.mp4", run_id)
        
        # PART 7: THUMBNAIL
        print("   [3/3] Generating Cinematic Thumbnail...")
        thumb_img = self.thumbnail_gen.generate_thumbnail(topic, "BIGGEST MISTAKE", os.path.join(full_path, "thumbnail.jpg"))

        print(f"\n[PIPELINE] COMPLETE!")
        print(f"      - Short: {short_video}")
        print(f"      - Full: {full_video}")
        print(f"      - Thumbnail: {thumb_img}")
        return run_path, actual_topic

    async def process_video_type(self, script_data, output_dir, filename, run_uuid):
        """Helper to render a video for a list of script scenes."""
        # 1. Voice
        script_data = await self.audio_engine.process_script(script_data)
        
        # 2. Images (Parallelized for Speed)
        print(f"   [ImageGen] Generating assets for {len(script_data)} scenes in parallel...")
        
        # PART 1: Seed locking for consistency
        run_seed = random.randint(1, 1000000)

        async def generate_single_scene(scene):
            s_id = scene["id"]
            base_prompt = scene.get("character_base_prompt", "")
            img, depth = await asyncio.to_thread(
                self.asset_gen.generate_scene_assets, 
                s_id, 
                scene["image_prompt"], 
                f"{run_uuid[:4]}_{filename[0]}",
                base_prompt=base_prompt,
                seed=run_seed
            )
            return s_id, img, depth

        tasks = [generate_single_scene(scene) for scene in script_data]
        results = await asyncio.gather(*tasks)
        
        images = {r[0]: r[1] for r in results if r[1]}
        depths = {r[0]: r[2] for r in results if r[2]}
        
        # 3. Composition
        final_video_name = filename
        scene_videos = self.composer.render_all_scenes(script_data, images, depths)
        
        if not scene_videos:
            return None
            
        final_video = self.composer.concatenate_with_transitions(scene_videos, output_filename=final_video_name)
        
        # Move concatenation result to output_dir
        if final_video and os.path.exists(final_video):
            target = os.path.join(output_dir, final_video_name)
            if os.path.exists(target): os.remove(target)
            # Ensure folder exists
            os.makedirs(output_dir, exist_ok=True)
            shutil.copy(final_video, target)
            return target
        return None
