import logging
import re
from pathlib import Path

from .tools.youtube_api import YouTubeUploader
from .tools.moderation import sanitize_for_display

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TAGS = 30
MAX_TAG_LENGTH = 30


def sanitize_metadata(text: str, max_length: int) -> str:
    clean = re.sub(r'[<>"\';`\\]', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:max_length]


def sanitize_tags(tags: list) -> list:
    cleaned = []
    for tag in tags:
        tag = re.sub(r'<[^>]+>', '', str(tag))
        tag = re.sub(r'[^a-zA-Z0-9_# ]', '', tag)
        tag = re.sub(r'\s+', ' ', tag).strip().lower()
        if tag and len(tag) <= MAX_TAG_LENGTH:
            cleaned.append(tag)
    return cleaned[:MAX_TAGS]


class UploadAgent:
    def __init__(self):
        self._uploader = None

    def _get_uploader(self):
        if self._uploader is None:
            try:
                self._uploader = YouTubeUploader()
            except Exception as e:
                logger.error(f"YouTube API init error: {e}")
                self._uploader = False
        return self._uploader if self._uploader is not False else None

    async def upload(self, state: dict) -> dict:
        video_path = state.get("video_path", "")
        seo = state.get("seo_metadata", {})
        thumbnail_path = state.get("thumbnail_url", "")
        auto_upload = state.get("auto_upload", False)
        review_before = state.get("review_before_upload", True)

        if not video_path or not Path(video_path).exists():
            logger.warning("No video file to upload")
            return {**state, "youtube_video_id": "", "youtube_url": "", "current_step": "analytics"}

        # Upload if auto_upload is enabled (the primary path for automation)
        # Only skip if review_before_upload is explicitly requested AND auto_upload is off
        if not auto_upload and review_before:
            logger.info("Upload paused — AUTO_UPLOAD=false and REVIEW_BEFORE_UPLOAD=true. Video saved locally.")
            return {**state, "youtube_video_id": "local_only", "youtube_url": "", "current_step": "analytics"}

        # auto_upload=false but review_before=false means upload anyway
        if not auto_upload:
            logger.info("AUTO_UPLOAD=false but REVIEW_BEFORE_UPLOAD=false — uploading")

        uploader = self._get_uploader()
        if not uploader:
            logger.warning("YouTube API not available, skipping upload")
            return {**state, "youtube_video_id": "local_only", "youtube_url": "", "current_step": "analytics"}

        logger.info("Uploading Short to YouTube...")

        tags = seo.get("tags", [])
        if "shorts" not in [t.lower() for t in tags]:
            tags.append("shorts")

        safe_title = sanitize_metadata(seo.get("title", "Breaking News"), MAX_TITLE_LENGTH)

        # Ensure #shorts is in the description — YouTube requires it for Shorts classification
        description = seo.get("description", "Breaking news update")
        hashtags = seo.get("hashtags") or []
        if not any("#shorts" in tag.lower() for tag in hashtags) and "#shorts" not in description.lower():
            description = description + "\n\n#shorts"
        safe_desc = sanitize_metadata(description, MAX_DESCRIPTION_LENGTH)

        safe_tags = sanitize_tags(tags)

        # Run blocking upload in a thread to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: uploader.upload(
                video_path=video_path,
                title=safe_title,
                description=safe_desc,
                tags=safe_tags,
                thumbnail_path=thumbnail_path if thumbnail_path and Path(thumbnail_path).exists() else None,
                privacy_status="public",
            )
        )

        if "error" in result:
            logger.error(f"Upload error: {result['error']}")
            return {**state, "youtube_video_id": "", "youtube_url": "", "current_step": "analytics"}

        logger.info(f"Uploaded: {result.get('url', '')}")
        return {
            **state,
            "youtube_video_id": result.get("id", ""),
            "youtube_url": result.get("url", ""),
            "current_step": "analytics",
        }
