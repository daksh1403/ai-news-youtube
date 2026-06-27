import httpx
from pathlib import Path
from datetime import datetime
import hashlib
import os
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class ImageGenerator:
    def __init__(self, provider: str = "pollinations", output_dir: str = "output/thumbnails"):
        self.provider = provider
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=60, follow_redirects=True)

    def generate(self, prompt: str, width: int = 1280, height: int = 720) -> str:
        import re
        safe_prompt = re.sub(r'[<>"\';`\\]', '', prompt)[:500]
        if self.provider == "pollinations":
            return self._pollinations(safe_prompt, width, height)
        elif self.provider == "together":
            return self._together(safe_prompt, width, height)
        return self._pollinations(safe_prompt, width, height)

    def _pollinations(self, prompt: str, width: int, height: int) -> str:
        import random
        encoded_prompt = quote(prompt, safe="")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.client.get(url, follow_redirects=True)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    filename = f"thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = self.output_dir / filename
                    filepath.write_bytes(resp.content)
                    return str(filepath)
                logger.warning(f"Pollinations returned status {resp.status_code}, size {len(resp.content)}")
            except Exception as e:
                logger.error(f"Pollinations error (attempt {attempt+1}): {e}")

            if attempt < max_retries - 1:
                import time
                time.sleep((attempt + 1) * 2 + random.uniform(0, 1))

        return self._create_placeholder(prompt, width, height)

    def _together(self, prompt: str, width: int, height: int) -> str:
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            return self._pollinations(prompt, width, height)

        try:
            resp = self.client.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "black-forest-labs/FLUX.1-schnell-Free",
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "steps": 4,
                    "n": 1,
                    "response_format": "b64_json",
                },
                timeout=60,
            )
            if resp.status_code == 200:
                import base64
                data = resp.json()
                if "data" in data and len(data["data"]) > 0:
                    b64 = data["data"][0].get("b64_json")
                    if b64:
                        filename = f"thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = self.output_dir / filename
                        filepath.write_bytes(base64.b64decode(b64))
                        return str(filepath)
            logger.warning(f"Together returned status {resp.status_code}")
        except Exception as e:
            logger.error(f"Together error: {e}")

        return self._pollinations(prompt, width, height)

    def _create_placeholder(self, prompt: str, width: int, height: int) -> str:
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (width, height), color=(15, 15, 25))
            draw = ImageDraw.Draw(img)

            lines = [prompt[i:i+40] for i in range(0, min(len(prompt), 120), 40)]
            y = height // 3
            for line in lines:
                draw.text((width // 4, y), line, fill=(0, 200, 255))
                y += 30

            filename = f"placeholder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.output_dir / filename
            img.save(filepath, "JPEG", quality=85)
            return str(filepath)
        except Exception as e:
            logger.error(f"Placeholder error: {e}")
            return ""
