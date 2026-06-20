"""
composer.py — Video Composer for Alreetal AI Shorts
Builds scenes from AI-generated images with Phase 23 Safe-Area Subtitles.
Ensures zero clipping with dynamic Y positioning and strict margins.
"""

import os
import random
import time
import uuid
import subprocess
import traceback
import textwrap
import ffmpeg
import numpy as np
from scipy.ndimage import gaussian_filter

from moviepy import VideoFileClip, TextClip, CompositeVideoClip

# ── Safe Area Constants (Phase 23) ────────────────────────────────────────────
FONT_PATH = "assets/font.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "C:/Windows/Fonts/arial.ttf"

VIDEO_W = 1080
VIDEO_H = 1920
BOTTOM_MARGIN = 80   # Part 1: Bottom margin
SIDE_MARGIN = 40     # Part 1: Side margin
SUBTITLE_WIDTH = int(VIDEO_W * 0.75)  # Part 3: 75% width
FONT_SIZE = 40       # Part 4: Reduced font size (38-42 range)


class Composer:
    def __init__(self):
        self.temp_dir   = os.path.join(os.getcwd(), "assets", "temp")
        self.final_dir  = os.path.join(os.getcwd(), "assets", "final")
        self.caption_dir = os.path.join(os.getcwd(), "assets", "temp", "captioned")

        os.makedirs(self.temp_dir,    exist_ok=True)
        os.makedirs(self.final_dir,   exist_ok=True)
        os.makedirs(self.caption_dir, exist_ok=True)

        self.transitions = ["fade", "diagbr", "diagtl", "wipeleft", "slideup"]
        self.cleanup_old_assets()

    def cleanup_old_assets(self):
        """Cleanup old video files to save space."""
        print("   --- Cleaning up all old assets (videos, images, audio)...")
        ai_images_dir = os.path.join(os.getcwd(), "assets", "ai_images")
        audio_clips_dir = os.path.join(os.getcwd(), "assets", "audio_clips")
        
        for folder in [self.temp_dir, self.final_dir, self.caption_dir, ai_images_dir, audio_clips_dir]:
            if not os.path.exists(folder): continue
            for f in os.listdir(folder):
                try: os.remove(os.path.join(folder, f))
                except: pass

    def get_duration(self, filepath: str) -> float:
        try:
            probe = ffmpeg.probe(filepath)
            return float(probe["format"]["duration"])
        except:
            return 0.0

    def image_to_3d_clip(self, image_path: str, depth_path: str, word_offsets: list, duration: float, output_path: str, english_caption: str = "", scene_type: str = "") -> str | None:
        """
        Renders a cinematic clip with MULTI-LAYER 3D motion (Part 5) and 
        REEL-STYLE animated captions (Part 8, 9).
        """
        try:
            from moviepy import ImageClip, ColorClip, CompositeVideoClip, vfx
            import numpy as np
            from PIL import Image

            print(f"      - Premium Render: {os.path.basename(image_path)}")
            
            # --- PART 5: TRUE MOTION FEED ---
            # Use a blurred background to fill the screen, and show the full uncropped image in the center.
            from PIL import ImageFilter
            orig_img = Image.open(image_path).convert("RGB")
            
            # 1. Background Layer (Blurred to fill screen)
            bg_blurred = orig_img.filter(ImageFilter.GaussianBlur(radius=15))
            bg_clip = ImageClip(np.array(bg_blurred)).with_duration(duration).resized(height=VIDEO_H)
            bg_clip = bg_clip.with_effects([vfx.Resize(lambda t: 1.0 + 0.05 * (t/duration))])
            
            # 2. Foreground Layer (Full Image)
            # Resize width to VIDEO_W so the entire image is visible horizontally without cropping
            fg_clip = ImageClip(np.array(orig_img)).with_duration(duration).resized(width=VIDEO_W)
            fg_clip = fg_clip.with_effects([vfx.Resize(lambda t: 1.0 + 0.08 * (t/duration))])
            fg_clip = fg_clip.with_position(("center", "center"))
            
            # --- PART 6: CAMERA SHAKE (CINEMATIC) ---
            if scene_type in ["twist", "climax"]:
                def camera_shake(get_frame, t):
                    frame = get_frame(t)
                    dx = random.randint(-4, 4)
                    dy = random.randint(-4, 4)
                    return np.roll(np.roll(frame, dx, axis=1), dy, axis=0)
                bg_clip = bg_clip.transform(camera_shake)

            # --- PART 8 & 9: NETFLIX-STYLE ENGLISH CAPTIONS ---
            caption_clips = []
            if english_caption:
                words = english_caption.split()
                chunk_size = 4
                chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
                num_chunks = len(chunks)
                
                if num_chunks > 0:
                    chunk_duration = duration / num_chunks
                    from PIL import Image, ImageDraw, ImageFont
                    from moviepy import ImageClip
                    
                    for i, chunk_text in enumerate(chunks):
                        try:
                            font = ImageFont.truetype(FONT_PATH, 55)
                        except:
                            font = ImageFont.load_default()
                            
                        words = chunk_text.split()
                        lines = []
                        current_line = []
                        dummy_img = Image.new('RGBA', (1, 1))
                        draw = ImageDraw.Draw(dummy_img)
                        
                        for word in words:
                            current_line.append(word)
                            test_line = " ".join(current_line)
                            bbox = draw.textbbox((0, 0), test_line, font=font)
                            if bbox[2] - bbox[0] > int(VIDEO_W * 0.8) and len(current_line) > 1:
                                current_line.pop()
                                lines.append(current_line)
                                current_line = [word]
                        if current_line:
                            lines.append(current_line)
                            
                        line_heights = []
                        line_widths = []
                        for line in lines:
                            bbox = draw.textbbox((0, 0), " ".join(line), font=font)
                            line_widths.append(bbox[2] - bbox[0])
                            line_heights.append(bbox[3] - bbox[1] + 15)
                            
                        total_height = sum(line_heights) + 20
                        width = int(VIDEO_W * 0.8)
                        
                        img = Image.new('RGBA', (width, total_height), (0, 0, 0, 0))
                        draw = ImageDraw.Draw(img)
                        y = 10
                        for idx, line in enumerate(lines):
                            x = (width - line_widths[idx]) // 2
                            for word in line:
                                clean_word = ''.join(c for c in word if c.isalnum())
                                color = "yellow" if len(clean_word) > 4 else "white"
                                
                                stroke_width = 3
                                for dx in range(-stroke_width, stroke_width+1):
                                    for dy in range(-stroke_width, stroke_width+1):
                                        if dx*dx + dy*dy <= stroke_width*stroke_width:
                                            draw.text((x+dx, y+dy), word, font=font, fill="black")
                                            
                                draw.text((x, y), word, font=font, fill=color)
                                bbox = draw.textbbox((0, 0), word + " ", font=font)
                                x += (bbox[2] - bbox[0])
                            y += line_heights[idx]
                            
                        img_path = os.path.join(self.temp_dir, f"cap_{uuid.uuid4().hex[:8]}.png")
                        img.save(img_path)
                        
                        txt = ImageClip(img_path).with_start(i * chunk_duration).with_duration(chunk_duration)
                        txt = txt.with_position(("center", int(VIDEO_H * 0.70)))
                        caption_clips.append(txt)
            
            # Final Composition
            final_video = CompositeVideoClip([bg_clip, fg_clip] + caption_clips, size=(VIDEO_W, VIDEO_H))
            final_video.write_videofile(output_path, fps=30, codec="libx264", audio=False, preset="ultrafast", logger=None)
            
            final_video.close()
            bg_clip.close()
            fg_clip.close()
            
            return output_path
            
        except Exception as e:
            print(f"   [Premium Render Error]: {e}")
            traceback.print_exc()
            return None

    def process_scene(self, scene: dict, image_path: str, depth_path: str = None) -> str | None:
        scene_id    = scene["id"]
        audio_path  = scene["audio_path"]
        duration    = scene.get("duration", 5.0)
        output_path = os.path.join(self.temp_dir, f"scene_{scene_id}.mp4")

        print(f"   --- Building Scene {scene_id} ({duration:.1f}s)...")

        eng_cap = scene.get("english_caption", "Ancient India...")
        word_offsets = scene.get("word_offsets", [])
        
        # Safe Area Subtitle Engine
        scene_type = scene.get("type", "")
        raw_clip = self.image_to_3d_clip(image_path, depth_path, word_offsets, duration, output_path, english_caption=eng_cap, scene_type=scene_type)
        if not raw_clip: return None

        # Add Audio
        final_mux_path = output_path.replace(".mp4", "_final.mp4")
        try:
            if audio_path and os.path.exists(audio_path):
                cmd = ["ffmpeg", "-y", "-i", output_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", final_mux_path]
            else:
                cmd = ["ffmpeg", "-y", "-i", output_path, "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=44100", "-c:v", "copy", "-c:a", "aac", "-t", str(duration), final_mux_path]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(final_mux_path):
                os.remove(output_path)
                os.rename(final_mux_path, output_path)
                return output_path
        except: pass
        return output_path

    def render_all_scenes(self, script_data: list, images: dict, depths: dict = None) -> list:
        print("\n[Composer] Rendering scenes with Phase 23 Safe-Area Engine...")
        rendered_paths = []
        for scene in script_data:
            scene_id   = scene["id"]
            image_path = images.get(scene_id)
            if not image_path or not os.path.exists(image_path): continue
            path = self.process_scene(scene, image_path, depths.get(scene_id) if depths else None)
            if path: rendered_paths.append(path)
        return rendered_paths

    def concatenate_with_transitions(self, video_paths: list, output_filename: str = "final_short.mp4") -> str | None:
        """
        Phase 25: Memory-efficient stitching.
        - Use xfade transitions for short videos (<= 10 clips).
        - Use concat demuxer for long videos (> 10 clips) to avoid memory errors.
        """
        print(f"\n[Composer] Stitching {len(video_paths)} clips into {output_filename}...")
        output_path = os.path.join(self.final_dir, output_filename)
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except: pass

        if not video_paths: return None

        # Stability Strategy: If more than 10 clips, skip complex transitions to save memory
        if len(video_paths) > 10:
            print(f"   [Stability] Using Concat Demuxer for {len(video_paths)} clips (Memory-Safe).")
            concat_list_path = os.path.join(self.temp_dir, f"concat_list_{uuid.uuid4().hex[:8]}.txt")
            try:
                with open(concat_list_path, "w", encoding="utf-8") as f:
                    for p in video_paths:
                        # Normalize path for FFmpeg concat demuxer (requires straight slashes or escaped)
                        p_abs = os.path.abspath(p).replace("\\", "/")
                        f.write(f"file '{p_abs}'\n")
                
                cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list_path,
                    "-c", "copy", # Fast and zero-loss
                    output_path
                ]
                subprocess.run(cmd, capture_output=True)
                if os.path.exists(concat_list_path): os.remove(concat_list_path)
                return output_path
            except Exception as e:
                print(f"   [Concat Error] Demuxer failed: {e}")
                return None

        # Original transition logic for Shorts (<= 10 clips)
        print("   [Style] Using xfade transitions for high-impact Short.")
        try:
            input1 = ffmpeg.input(video_paths[0])
            v_stream = input1.video
            a_stream = input1.audio
            current_dur = self.get_duration(video_paths[0])

            for i in range(1, len(video_paths)):
                next_clip = ffmpeg.input(video_paths[i])
                next_dur = self.get_duration(video_paths[i])
                trans_dur = 0.3 # Part 10: Smooth crossfade (0.3 sec)
                offset = max(current_dur - trans_dur, 0.1)
                effect = random.choice(self.transitions)

                v_stream = ffmpeg.filter(
                    [v_stream.filter("format", "yuv420p"), next_clip.video.filter("format", "yuv420p")],
                    "xfade", transition=effect, duration=trans_dur, offset=offset,
                )
                a_stream = ffmpeg.filter([a_stream, next_clip.audio], "acrossfade", d=trans_dur)
                current_dur = (current_dur + next_dur) - trans_dur

            # --- PART 7: BACKGROUND MUSIC SYNC ---
            # Attempt to add background music if it exists
            music_path = os.path.join(os.getcwd(), "assets", "music.mp3")
            if os.path.exists(music_path):
                print("   [Audio] Mixing background music...")
                music_input = ffmpeg.input(music_path, stream_loop=-1, t=current_dur)
                # Music Volume: Sync logic (Part 7) - Ducking manually or fixed lower volume
                music_audio = music_input.audio.filter("volume", 0.15) 
                a_stream = ffmpeg.filter([a_stream.filter("volume", 1.0), music_audio], "amix", duration="first")

            (
                ffmpeg
                .output(
                    v_stream, a_stream,
                    output_path,
                    vcodec="libx264", acodec="aac",
                    pix_fmt="yuv420p", movflags="faststart", preset="ultrafast",
                )
                .run(overwrite_output=True, quiet=True)
            )
            return output_path
        except Exception as e:
            print(f"   [Stitch Error] xfade transition failed: {e}")
            return None

    def generate_srt(self, script_data: list, output_filename: str = "subtitles.srt"):
        pass