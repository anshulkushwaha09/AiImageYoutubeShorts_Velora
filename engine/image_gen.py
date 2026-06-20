import os
from modules.multi_image_generator import MultiImageGenerator
from engine.video_logic import generate_pseudo_depth

class ImageDepthDualGenerator:
    def __init__(self):
        self.image_gen = MultiImageGenerator()
        
    def generate_scene_assets(self, scene_id: int, image_prompt: str, unique_id: str, base_prompt: str = "", seed: int = None):
        """
        1. Generate Image using Multi-API Fallback with Character Consistency.
        2. Generate high-contrast pseudo-depth map LOCALLY.
        """
        image_path = self.image_gen.generate_image(scene_id, image_prompt, base_prompt=base_prompt, seed=seed)
        
        # Get the actual filename created by the generator to stay in sync
        filename = os.path.basename(image_path).replace(".png", "_depth.png")
        depth_path = os.path.join(self.image_gen.output_dir, filename)
        
        # 2. Local Depth Generation
        final_depth_path = generate_pseudo_depth(image_path, depth_path)
        
        return image_path, final_depth_path
