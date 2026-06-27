"""Run YouTube OAuth flow to generate access token.

Usage:
    python scripts/auth_youtube.py

This will open a browser window. Sign in with your YouTube account
to authorize the app. The token will be saved to config/youtube_token.json.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS = Path(__file__).parent.parent / "config" / "client_secrets.json"
TOKEN_PATH = Path(__file__).parent.parent / "config" / "youtube_token.json"


def main():
    if not CLIENT_SECRETS.exists():
        print(f"ERROR: {CLIENT_SECRETS} not found.")
        print("Please create it first with your YouTube API credentials.")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    print("Starting YouTube OAuth flow...")
    print("A browser window will open. Sign in with your YouTube account.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    creds = flow.run_local_server(port=8090)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f, indent=2)

    print()
    print(f"SUCCESS! Token saved to {TOKEN_PATH}")
    print(f"  Token: {creds.token[:20]}...")
    print(f"  Refresh token: {creds.refresh_token[:20]}...")

    # Verify the token works
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=creds)
    response = youtube.channels().list(part="snippet", mine=True).execute()
    if response.get("items"):
        channel = response["items"][0]["snippet"]
        print(f"  Channel: {channel.get('title', 'Unknown')}")
    print()
    print("YouTube upload is now configured!")


if __name__ == "__main__":
    main()
