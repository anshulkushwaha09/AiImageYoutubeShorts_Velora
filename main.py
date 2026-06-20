import asyncio
import os
import argparse
from modules.pipeline import ContentPipeline

async def main():
    parser = argparse.ArgumentParser(description="Alreetal AI mythology Video Pipeline")
    parser.add_argument("--topic", type=str, default="", help="Topic for the video (leave empty for auto-generated topic)")
    parser.add_argument("--upload", action="store_true", help="Upload the generated video to YouTube automatically")
    args = parser.parse_args()

    pipeline = ContentPipeline()
    
    # Fetch a trending topic if not provided
    topic = args.topic
    if not topic:
        from modules.brain import ContentBrain
        brain = ContentBrain()
        topic = brain.get_trending_topic()
    
    # Part 10 & 11: Complete Automated Content Pipeline
    # Generates Short, Full Video, and Thumbnail in one run.
    print("\n--- [ALREETAL AI CONTENT ENGINE] ---")
    print(f"Target Topic: {topic}\n")
    
    try:
        output_data = await pipeline.generate_full_pipeline(topic)
        
        if output_data:
            output_path, actual_topic = output_data if isinstance(output_data, tuple) else (output_data, topic)
            
            print(f"\n[Success] ALL ASSETS GENERATED SUCCESSFULLY!")
            print(f"   Storage: {output_path}")
            print(f"   Contents: /short/video.mp4, /full/video.mp4, /full/thumbnail.jpg")
            
            if args.upload:
                from modules.youtube_uploader import YouTubeUploader
                uploader = YouTubeUploader()
                
                # We upload the full video (since short generation is currently skipped in pipeline)
                full_video = os.path.join(output_path, "full", "full.mp4")
                thumbnail = os.path.join(output_path, "full", "thumbnail.jpg")
                
                if os.path.exists(full_video):
                    title = f"{actual_topic} | Untold Mystery Explained! 😲🔥 #shorts"
                    desc = f"Dive deep into the shocking truth about {actual_topic}! 🤯 Watch this cinematic AI-generated story to uncover ancient mysteries and hidden secrets.\n\n🔔 Subscribe for more mind-blowing mythological stories and facts!\n\n#Mythology #History #AI #SanatanDharma #AncientIndia #Trending #Shorts"
                    uploader.upload_video(full_video, thumbnail, title, desc)
                else:
                    print("   [Upload Warning] Full video not found for upload.")
                    
        else:
            print("\n[Error] Pipeline failed to complete all steps.")
            
    except Exception as e:
        print(f"\n[Fatal Error] Pipeline crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())