import json
import logging
import random
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from .tools.llm_router import LLMRouter
from .tools.image_gen import ImageGenerator

logger = logging.getLogger(__name__)


# --- Color palettes for eye-catching Shorts thumbnails ---
PALETTES = [
    {"bg": (220, 20, 60), "accent": (255, 215, 0), "text": (255, 255, 255)},   # Red + Gold
    {"bg": (0, 100, 200), "accent": (0, 255, 180), "text": (255, 255, 255)},  # Blue + Teal
    {"bg": (30, 30, 30), "accent": (255, 69, 0), "text": (255, 255, 255)},    # Dark + Red-Orange
    {"bg": (75, 0, 130), "accent": (255, 105, 180), "text": (255, 255, 255)}, # Purple + Pink
    {"bg": (0, 150, 80), "accent": (255, 255, 0), "text": (255, 255, 255)},   # Green + Yellow
]

# Category-specific palette overrides
CATEGORY_COLORS = {
    "tech": [(0, 100, 200), (0, 255, 180)],
    "ai": [(30, 30, 30), (0, 200, 255)],
    "science": [(0, 150, 80), (255, 255, 0)],
    "politics": [(180, 20, 20), (255, 215, 0)],
    "business": [(0, 80, 160), (255, 255, 255)],
    "general": [(220, 20, 60), (255, 215, 0)],
}


class ThumbnailAgent:
    WIDTH = 1080
    HEIGHT = 1920

    def __init__(self):
        self.router = LLMRouter()
        self.image_gen = ImageGenerator()
        self.output_dir = Path("output/thumbnails")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, state: dict) -> dict:
        article = state.get("selected_article", {})
        seo = state.get("seo_metadata", {})

        if not article:
            return {**state, "thumbnail_url": "", "current_step": "narrator"}

        logger.info("Generating eye-catching Shorts thumbnail...")

        title = seo.get("title", article.get("title", "Breaking News"))
        category = article.get("category", "general")
        hook = state.get("script", {}).get("hook", "")

        # Pick a vibrant palette based on category
        palette = self._pick_palette(category)

        # Generate base AI image
        prompt = f"""Create a dramatic YouTube Shorts thumbnail image.

Title: {title}
Topic: {article.get('title', '')}
Category: {category}

Style: vertical 9:16, cinematic lighting, high contrast, saturated colors,
cyberpunk news aesthetic, one dramatic focal point, bokeh background,
no text in the image. Professional photography quality.

Return ONLY a detailed image prompt (2-3 sentences)."""

        try:
            img_prompt = await self.router.invoke(prompt, task="fast")
            img_prompt = img_prompt.strip().strip('"').strip("'")
            if img_prompt.startswith("{"):
                img_prompt = json.loads(img_prompt).get("prompt", title)
        except Exception:
            img_prompt = f"Dramatic cinematic news photo, {category}, {title[:60]}"

        base_path = self.image_gen.generate(img_prompt, width=self.WIDTH, height=self.HEIGHT)

        # Apply eye-catching post-processing
        enhanced_path = self._apply_effects(
            base_path, title, hook, category, palette
        )

        logger.info(f"Thumbnail: {enhanced_path}")
        return {**state, "thumbnail_url": enhanced_path, "current_step": "narrator"}

    def _pick_palette(self, category: str) -> dict:
        """Choose a color palette based on news category."""
        colors = CATEGORY_COLORS.get(category.lower(), None)
        if colors:
            return {"bg": colors[0], "accent": colors[1], "text": (255, 255, 255)}
        return random.choice(PALETTES)

    def _apply_effects(
        self, image_path: str, title: str, hook: str, category: str, palette: dict
    ) -> str:
        """Apply eye-catching visual effects to the thumbnail."""
        try:
            img = Image.open(image_path).convert("RGB")
            img = img.resize((self.WIDTH, self.HEIGHT), Image.LANCZOS)

            # 1. Boost contrast and saturation for punch
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Color(img).enhance(1.4)
            img = ImageEnhance.Brightness(img).enhance(1.05)

            # 2. Add cinematic vignette (dark edges)
            img = self._add_vignette(img)

            # 3. Add gradient overlay at bottom for text legibility
            img = self._add_bottom_gradient(img, palette["bg"])

            # 4. Add category badge at top-left
            img = self._add_category_badge(img, category, palette)

            # 5. Add bold title text
            img = self._add_title_text(img, title, palette)

            # 6. Add "BREAKING" or hook text at top
            display_hook = hook[:30] if hook else "BREAKING NEWS"
            img = self._add_top_banner(img, display_hook, palette)

            # Save enhanced thumbnail
            filename = f"thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            out_path = self.output_dir / filename
            img.save(str(out_path), "JPEG", quality=92)

            return str(out_path)

        except Exception as e:
            logger.error(f"Thumbnail effects failed: {e}")
            return image_path

    def _add_vignette(self, img: Image.Image) -> Image.Image:
        """Add a subtle dark vignette around the edges."""
        vignette = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        cx, cy = img.size[0] // 2, img.size[1] // 2
        max_r = int((cx**2 + cy**2) ** 0.5)

        for r in range(max_r, 0, -4):
            alpha = int(100 * (r / max_r) ** 2)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, alpha))

        img_rgba = img.convert("RGBA")
        return Image.alpha_composite(img_rgba, vignette).convert("RGB")

    def _add_bottom_gradient(self, img: Image.Image, color: tuple) -> Image.Image:
        """Add a gradient overlay at the bottom half for text readability."""
        gradient = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)

        h = img.size[1]
        start_y = int(h * 0.45)

        for y in range(start_y, h):
            progress = (y - start_y) / (h - start_y)
            alpha = int(220 * progress)
            r = int(color[0] * progress * 0.4)
            g = int(color[1] * progress * 0.4)
            b = int(color[2] * progress * 0.4)
            draw.line([(0, y), (img.size[0], y)], fill=(r, g, b, alpha))

        img_rgba = img.convert("RGBA")
        return Image.alpha_composite(img_rgba, gradient).convert("RGB")

    def _add_category_badge(self, img: Image.Image, category: str, palette: dict) -> Image.Image:
        """Add a small colored badge with the category name."""
        draw = ImageDraw.Draw(img)
        label = category.upper()[:12]

        font = self._get_font(size=28)
        bbox = font.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        pad_x, pad_y = 20, 10
        x0, y0 = 40, 60
        x1 = x0 + tw + pad_x * 2
        y1 = y0 + th + pad_y * 2

        # Badge background with accent color
        draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=palette["accent"])
        draw.text((x0 + pad_x, y0 + pad_y - 4), label, fill=palette["bg"], font=font)

        return img

    def _add_top_banner(self, img: Image.Image, text: str, palette: dict) -> Image.Image:
        """Add a bold banner at the very top with hook/breaking text."""
        draw = ImageDraw.Draw(img)

        font = self._get_font(size=36, bold=True)
        bbox = font.getbbox(text.upper())
        tw = bbox[2] - bbox[0]

        banner_h = 90
        y_start = 120

        # Semi-transparent dark banner
        banner = Image.new("RGBA", (img.size[0], banner_h), (0, 0, 0, 180))
        img_rgba = img.convert("RGBA")
        img_rgba.paste(banner, (0, y_start), banner)

        draw = ImageDraw.Draw(img_rgba)
        # Center text
        tx = (img.size[0] - tw) // 2
        ty = y_start + (banner_h - 36) // 2 - 4
        draw.text((tx, ty), text.upper(), fill=palette["accent"], font=font)

        return img_rgba.convert("RGB")

    def _add_title_text(self, img: Image.Image, title: str, palette: dict) -> Image.Image:
        """Add bold, wrapped title text in the lower portion of the thumbnail."""
        draw = ImageDraw.Draw(img)
        font = self._get_font(size=52, bold=True)

        # Word-wrap the title
        lines = self._wrap_text(draw, title.upper(), font, self.WIDTH - 120)
        lines = lines[:5]  # Max 5 lines

        line_height = 62
        total_text_h = len(lines) * line_height
        y_start = self.HEIGHT - total_text_h - 280

        for i, line in enumerate(lines):
            bbox = font.getbbox(line)
            tw = bbox[2] - bbox[0]
            x = (self.WIDTH - tw) // 2
            y = y_start + i * line_height

            # Text shadow for depth
            draw.text((x + 3, y + 3), line, fill=(0, 0, 0), font=font)
            # Main text
            draw.text((x, y), line, fill=palette["text"], font=font)

        return img

    @staticmethod
    def _wrap_text(draw, text: str, font, max_width: int) -> list:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _get_font(self, size: int = 48, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Try to load a bold system font, fall back to default."""
        candidates = []
        if bold:
            candidates += [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "C:/Windows/Fonts/verdanab.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFNSText.ttf",
            ]
        candidates += [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()
