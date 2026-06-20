import os
import pickle
import base64
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeUploader:
    def __init__(self):
        self.youtube = None

    def authenticate(self):
        creds = None
        
        # In GitHub Actions, we read the token from environment
        b64_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
        if b64_token:
            print("   [YouTube] Loading credentials from environment variable...")
            try:
                creds = pickle.loads(base64.b64decode(b64_token))
            except Exception as e:
                print(f"   [YouTube Error] decoding token: {e}")
        elif os.path.exists('token.pickle'):
            print("   [YouTube] Loading credentials from token.pickle file...")
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("   [YouTube] Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("   [YouTube Error] No valid credentials found. Cannot upload.")
                return False
                
        self.youtube = build('youtube', 'v3', credentials=creds)
        return True

    def upload_video(self, video_path: str, thumbnail_path: str, title: str, description: str, tags: list = None):
        if not self.youtube:
            if not self.authenticate():
                return False
                
        print(f"\n[YouTube] Starting upload for: {title}")
        
        if not tags:
            tags = ["shorts", "mythology", "history", "ai"]
            
        body = {
            'snippet': {
                'title': title[:100], # YouTube max title length is 100
                'description': description,
                'tags': tags,
                'categoryId': '27' # Education
            },
            'status': {
                'privacyStatus': 'public', # Make video public
                'selfDeclaredMadeForKids': False
            }
        }
        
        try:
            print("   -> Uploading video file...")
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            response = request.execute()
            video_id = response.get('id')
            print(f"   [Success] Video uploaded! ID: {video_id}")
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                print("   -> Uploading thumbnail...")
                self.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                print("   [Success] Thumbnail uploaded!")
                
            return f"https://youtu.be/{video_id}"
            
        except Exception as e:
            print(f"   [YouTube Upload Error] {e}")
            return None
