import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class YouTubeUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    TOKEN_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "youtube_token.json"
    CLIENT_SECRETS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "client_secrets.json"

    def __init__(self):
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            logger.error("google-api-python-client not installed")
            return

        creds = None

        # Strategy 1: Load from local token file
        if self.TOKEN_PATH.exists():
            try:
                with open(self.TOKEN_PATH, "r") as f:
                    token_data = json.load(f)
                creds = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes"),
                )
            except Exception as e:
                logger.error(f"Failed to load token: {e}")
                creds = None

        # Strategy 2: Build creds from environment variables (for CI/CD)
        if not creds:
            refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
            client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
            client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
            if refresh_token and client_id and client_secret:
                try:
                    creds = Credentials(
                        token=None,
                        refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=self.SCOPES,
                    )
                    logger.info("Loaded YouTube credentials from environment variables")
                except Exception as e:
                    logger.error(f"Failed to build creds from env: {e}")
                    creds = None

        if not creds:
            logger.warning("No YouTube credentials found (no token file or env vars). Upload disabled.")
            return

        # Refresh if expired or has no token
        if creds:
            if not creds.valid:
                if creds.expired or creds.token is None:
                    try:
                        creds.refresh(Request())
                        logger.info("YouTube token refreshed successfully")
                    except Exception as e:
                        logger.error(f"Token refresh failed: {e}")
                        # Try to re-authenticate from env vars
                        refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
                        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
                        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
                        if refresh_token and client_id and client_secret:
                            try:
                                creds = Credentials(
                                    token=None,
                                    refresh_token=refresh_token,
                                    token_uri="https://oauth2.googleapis.com/token",
                                    client_id=client_id,
                                    client_secret=client_secret,
                                    scopes=self.SCOPES,
                                )
                                creds.refresh(Request())
                                logger.info("Re-authenticated from env vars after token refresh failure")
                            except Exception as e2:
                                logger.error(f"Re-authentication also failed: {e2}")
                                creds = None
                        else:
                            creds = None

        # Save refreshed token locally for next time
        if creds:
            try:
                self.TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                token_data = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else self.SCOPES,
                }
                with open(self.TOKEN_PATH, "w") as f:
                    json.dump(token_data, f)
            except Exception as e:
                logger.warning(f"Failed to save refreshed token: {e}")

        if creds:
            try:
                self.youtube = build("youtube", "v3", credentials=creds)
            except Exception as e:
                logger.error(f"Failed to build YouTube service: {e}")

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        category_id: str = "28",
        thumbnail_path: str = None,
        privacy_status: str = "public",
    ) -> dict:
        if not self.youtube:
            return {"error": "YouTube API not authenticated"}

        if not Path(video_path).exists():
            return {"error": f"Video file not found: {video_path}"}

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024 * 10,
            )

            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Upload {int(status.progress() * 100)}%")

            video_id = response["id"]

            if thumbnail_path and Path(thumbnail_path).exists():
                self._set_thumbnail(video_id, thumbnail_path)

            return {
                "id": video_id,
                "url": f"https://youtube.com/watch?v={video_id}",
                "status": "uploaded",
            }

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {"error": str(e)}

    def _set_thumbnail(self, video_id: str, thumbnail_path: str):
        try:
            from googleapiclient.http import MediaFileUpload
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
        except Exception as e:
            logger.error(f"Thumbnail error: {e}")

    def get_analytics(self, video_id: str) -> dict:
        if not self.youtube:
            return {}

        try:
            response = self.youtube.videos().list(
                part="statistics",
                id=video_id,
            ).execute()

            if response["items"]:
                stats = response["items"][0]["statistics"]
                return {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                }
        except Exception as e:
            logger.error(f"Analytics error: {e}")

        return {}
