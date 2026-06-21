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
        self.whoosh_path = os.path.join(os.getcwd(), "assets", "sfx_whoosh.wav")
        self.ensure_whoosh_sfx()
        self.cleanup_old_assets()

    def ensure_whoosh_sfx(self):
        """Generates a synthetic whoosh sound effect using numpy if it doesn't exist."""
        if os.path.exists(self.whoosh_path):
            return
        
        print("   [Composer] Synthesizing custom whoosh sound effect...")
        try:
            import wave
            import numpy as np

            sr = 44100
            duration = 0.8
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)
            
            # White noise
            noise = np.random.normal(0, 0.15, len(t))
            
            # Amplitude envelope: bell curve (sine wave squared)
            envelope = np.sin(np.pi * t / duration) ** 2
            
            # Frequency sweep: low rumble (swept sine) + swept lowpass noise
            f_start = 80
            f_end = 350
            freq = f_start + (f_end - f_start) * (t / duration)
            phase = 2 * np.pi * np.cumsum(freq) / sr
            rumble = np.sin(phase) * 0.3
            
            # Swept IIR filter
            alpha_sweep = 0.98 - 0.15 * np.sin(np.pi * t / duration)
            y = np.zeros_like(noise)
            for i in range(1, len(noise)):
                a = alpha_sweep[i]
                y[i] = a * y[i-1] + (1 - a) * noise[i]
                
            signal = (y + rumble) * envelope
            # Normalize
            max_val = np.max(np.abs(signal))
            if max_val > 0:
                signal = signal / max_val * 0.5
            
            # Convert to 16-bit PCM
            signal_pcm = (signal * 32767).astype(np.int16)
            
            # Write to WAV
            with wave.open(self.whoosh_path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(signal_pcm.tobytes())
            print(f"   [Composer Done] Synthesized custom whoosh SFX at: {self.whoosh_path}")
        except Exception as e:
            print(f"   [Composer Warning] Failed to synthesize whoosh SFX: {e}")

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

            # --- PART 8 & 9: HIGH-RETENTION WORD-BY-WORD ACTIVE CAPTIONS ---
            caption_clips = []
            if english_caption:
                words = english_caption.split()
                num_words = len(words)
                
                if num_words > 0:
                    from PIL import Image, ImageDraw, ImageFont
                    from moviepy import ImageClip
                    
                    try:
                        font_reg = ImageFont.truetype(FONT_PATH, 52)
                        font_act = ImageFont.truetype(FONT_PATH, 60)
                    except:
                        font_reg = ImageFont.load_default()
                        font_act = ImageFont.load_default()
                        
                    # Estimate space width
                    dummy_img = Image.new('RGBA', (1, 1))
                    draw = ImageDraw.Draw(dummy_img)
                    space_bbox = draw.textbbox((0, 0), " ", font=font_reg)
                    space_w = space_bbox[2] - space_bbox[0] if (space_bbox[2] - space_bbox[0]) > 0 else 15
                    
                    # 1. Wrap words into lines while tracking original index
                    max_width = int(VIDEO_W * 0.85)
                    lines = []
                    current_line = []
                    current_width = 0
                    
                    for idx, word in enumerate(words):
                        # Measure word width
                        w_bbox = draw.textbbox((0, 0), word, font=font_reg)
                        word_w = w_bbox[2] - w_bbox[0]
                        
                        if current_width + word_w > max_width and current_line:
                            lines.append(current_line)
                            current_line = []
                            current_width = 0
                            
                        current_line.append((word, idx, word_w))
                        current_width += word_w + space_w
                        
                    if current_line:
                        lines.append(current_line)
                        
                    # Calculate word durations (even distribution over scene duration)
                    word_duration = duration / num_words
                    
                    # 2. Render a frame for each word index
                    for active_idx in range(num_words):
                        # Calculate layout heights
                        line_heights = []
                        line_widths = []
                        for line in lines:
                            # Width is sum of word widths + spaces
                            l_width = sum(w[2] for w in line) + space_w * (len(line) - 1)
                            # Height is max bbox height
                            l_heights = []
                            for w, idx, _ in line:
                                font = font_act if idx == active_idx else font_reg
                                bbox = draw.textbbox((0, 0), w, font=font)
                                l_heights.append(bbox[3] - bbox[1])
                            l_height = max(l_heights) + 15 if l_heights else 60
                            line_widths.append(l_width)
                            line_heights.append(l_height)
                            
                        total_height = sum(line_heights) + 20
                        canvas_width = int(VIDEO_W * 0.9)
                        
                        img = Image.new('RGBA', (canvas_width, total_height), (0, 0, 0, 0))
                        draw_frame = ImageDraw.Draw(img)
                        
                        y = 10
                        for l_idx, line in enumerate(lines):
                            # Center the line on canvas
                            line_w = line_widths[l_idx]
                            x = (canvas_width - line_w) // 2
                            
                            for w, idx, _ in line:
                                is_active = (idx == active_idx)
                                font = font_act if is_active else font_reg
                                color = "#FFD700" if is_active else "#FFFFFF" # Golden active, White regular
                                
                                # Measure exact word size with its specific font
                                bbox = draw_frame.textbbox((0, 0), w, font=font)
                                w_w = bbox[2] - bbox[0]
                                
                                # Draw Outline/Stroke (3px)
                                stroke_width = 3
                                for dx in range(-stroke_width, stroke_width+1):
                                    for dy in range(-stroke_width, stroke_width+1):
                                        if dx*dx + dy*dy <= stroke_width*stroke_width:
                                            draw_frame.text((x+dx, y+dy), w, font=font, fill="black")
                                            
                                # Draw Main Text
                                draw_frame.text((x, y), w, font=font, fill=color)
                                x += w_w + space_w
                                
                            y += line_heights[l_idx]
                            
                        # Save frame
                        img_path = os.path.join(self.temp_dir, f"cap_{uuid.uuid4().hex[:8]}.png")
                        img.save(img_path)
                        
                        # Create moviepy clip
                        start_time = active_idx * word_duration
                        # Ensure last clip goes to the exact end of scene to prevent black screen
                        clip_dur = word_duration if active_idx < num_words - 1 else (duration - start_time)
                        
                        txt = ImageClip(img_path).with_start(start_time).with_duration(clip_dur)
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

        # Add Audio & SFX Whoosh at scene transitions
        final_mux_path = output_path.replace(".mp4", "_final.mp4")
        try:
            if audio_path and os.path.exists(audio_path):
                if scene_id > 1 and os.path.exists(self.whoosh_path):
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", output_path,
                        "-i", audio_path,
                        "-i", self.whoosh_path,
                        "-filter_complex", "[1:a]volume=1.0[a1];[2:a]volume=0.30[a2];[a1][a2]amix=inputs=2:duration=first",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        final_mux_path
                    ]
                else:
                    cmd = ["ffmpeg", "-y", "-i", output_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", final_mux_path]
            else:
                if scene_id > 1 and os.path.exists(self.whoosh_path):
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", output_path,
                        "-i", self.whoosh_path,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        final_mux_path
                    ]
                else:
                    cmd = ["ffmpeg", "-y", "-i", output_path, "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=44100", "-c:v", "copy", "-c:a", "aac", "-t", str(duration), final_mux_path]
            
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(final_mux_path):
                os.remove(output_path)
                os.rename(final_mux_path, output_path)
                return output_path
        except Exception as e:
            print(f"   [Audio Mux Warning] Audio mux failed for scene {scene_id}: {e}")
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

        # Stability Strategy: If more than 10 clips, transcode via MPEG-2 TS for stability and speed
        if len(video_paths) > 10:
            print(f"   [Stability] Using TS Transcode Concat for {len(video_paths)} clips (Memory-Safe).")
            ts_paths = []
            try:
                # 1. Convert all clips to TS
                for p in video_paths:
                    ts_path = p.replace(".mp4", ".ts")
                    ts_paths.append(ts_path)
                    cmd = [
                        "ffmpeg", "-y", "-i", p,
                        "-c", "copy",
                        "-bsf:v", "h264_mp4toannexb",
                        "-f", "mpegts",
                        ts_path
                    ]
                    subprocess.run(cmd, capture_output=True)
                
                # 2. Concat demuxer with re-encoding to temp file
                concat_str = "concat:" + "|".join(ts_paths)
                temp_stitched = os.path.join(self.temp_dir, f"temp_ts_stitched_{uuid.uuid4().hex[:8]}.mp4")
                
                cmd_concat = [
                    "ffmpeg", "-y",
                    "-i", concat_str,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    temp_stitched
                ]
                subprocess.run(cmd_concat, capture_output=True)
                
                # 3. Clean up TS files immediately
                for ts in ts_paths:
                    if os.path.exists(ts): os.remove(ts)
                
                # 4. Check for background music and mix
                music_path = os.path.join(os.getcwd(), "assets", "music.mp3")
                if os.path.exists(music_path) and os.path.exists(temp_stitched):
                    print("   [Audio] Mixing background music with sidechain ducking...")
                    cmd_mix = [
                        "ffmpeg", "-y",
                        "-i", temp_stitched,
                        "-stream_loop", "-1", "-i", music_path,
                        "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=0.12[a2];[a1][a2]amix=inputs=2:duration=first",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        output_path
                    ]
                    subprocess.run(cmd_mix, capture_output=True)
                    if os.path.exists(temp_stitched): os.remove(temp_stitched)
                else:
                    if os.path.exists(temp_stitched):
                        if os.path.exists(output_path): os.remove(output_path)
                        os.rename(temp_stitched, output_path)
                
                return output_path
            except Exception as e:
                print(f"   [Concat Error] TS Transcode Concat failed: {e}")
                # Clean up any leftover TS files
                for ts in ts_paths:
                    if os.path.exists(ts):
                        try: os.remove(ts)
                        except: pass
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

            # --- PART 7: BACKGROUND MUSIC SYNC WITH SIDECHAIN DUCKING ---
            # Attempt to add background music if it exists
            music_path = os.path.join(os.getcwd(), "assets", "music.mp3")
            if os.path.exists(music_path):
                print("   [Audio] Mixing background music with sidechain ducking...")
                music_input = ffmpeg.input(music_path, stream_loop=-1, t=current_dur)
                # Base music volume is slightly higher, it gets compressed when narration plays
                music_audio = music_input.audio.filter("volume", 0.22) 
                
                try:
                    # Apply sidechaincompress: trigger on a_stream (narration) to duck music_audio
                    compressed_music = ffmpeg.filter([music_audio, a_stream], "sidechaincompress", threshold="-25dB", ratio=5, attack=50, release=250)
                    a_stream = ffmpeg.filter([a_stream, compressed_music], "amix", duration="first")
                except Exception as e:
                    print(f"   [Audio Sync Warning] Sidechain compression failed: {e}. Falling back to standard mix.")
                    music_audio_fallback = music_input.audio.filter("volume", 0.12)
                    a_stream = ffmpeg.filter([a_stream, music_audio_fallback], "amix", duration="first")

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
        except ffmpeg.Error as e:
            print(f"   [Stitch Error] xfade transition failed: {e}")
            if e.stderr:
                print("FFmpeg Stderr:")
                print(e.stderr.decode('utf-8', errors='replace'))
            return None
        except Exception as e:
            print(f"   [Stitch Error] xfade transition failed: {e}")
            return None

    def generate_srt(self, script_data: list, output_filename: str = "subtitles.srt"):
        pass