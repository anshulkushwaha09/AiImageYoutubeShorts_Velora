import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    if not os.path.exists("client_secrets.json"):
        print("Error: client_secrets.json not found in the current directory.")
        print("Please download it from the Google Cloud Console.")
        return

    print("Authenticating with YouTube... This will open your browser.")
    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    creds = flow.run_local_server(port=0)

    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
        
    print("\nSUCCESS! token.pickle has been generated.")
    print("Keep this file secret. You will need to Base64 encode it for GitHub Actions.")
    
    # Generate Base64 string automatically for the user
    import base64
    with open('token.pickle', 'rb') as f:
        b64_token = base64.b64encode(f.read()).decode('utf-8')
    
    print("\n=== YOUR YOUTUBE_OAUTH_TOKEN SECRET FOR GITHUB ACTIONS ===")
    print(b64_token)
    print("==========================================================")

if __name__ == "__main__":
    main()
