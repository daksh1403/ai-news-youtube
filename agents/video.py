import subprocess
import logging
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoAgent:
    WIDTH = 1080
    HEIGHT = 1920

    def __init__(self):
        self.output_dir = Path("output/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._ffmpeg_available = None
        self._ffmpeg_cmd = "ffmpeg"
        self._ffprobe_cmd = "ffprobe"

    def _check_ffmpeg(self) -> bool:
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                self._ffmpeg_available = True
                return True
        except FileNotFoundError:
            pass
        except Exception:
            pass

        search_paths = [
            # macOS (Homebrew / MacPorts)
            Path("/opt/homebrew/bin/ffmpeg"),
            Path("/usr/local/bin/ffmpeg"),
            Path.home() / "homebrew/bin/ffmpeg",
            # Linux
            Path("/usr/bin/ffmpeg"),
            Path("/usr/local/bin/ffmpeg"),
            # Windows
            Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe",
            Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
            Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
            Path(    r"C:\tools\ffmpeg\bin\ffmpeg.exe"),
            Path.home() / "scoop/shims/ffmpeg.exe",
            Path.home() / "ffmpeg/bin/ffmpeg.exe",
            # Linux/WSL common paths
            Path("/snap/bin/ffmpeg"),
            Path("/usr/local/bin/ffmpeg"),
        ]
        for ffmpeg_path in search_paths:
            if ffmpeg_path.exists():
                self._ffmpeg_available = True
                self._ffmpeg_cmd = str(ffmpeg_path)
                # Try ffprobe.exe (Windows) first, then ffprobe (macOS/Linux)
                ffprobe_win = ffmpeg_path.parent / "ffprobe.exe"
                ffprobe_unix = ffmpeg_path.parent / "ffprobe"
                self._ffprobe_cmd = str(ffprobe_win if ffprobe_win.exists() else ffprobe_unix)
                return True

        # Final fallback: try "ffmpeg" from PATH (handles WSL, conda, virtualenvs)
        import shutil
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            self._ffmpeg_available = True
            self._ffmpeg_cmd = ffmpeg_in_path
            ffprobe_path = shutil.which("ffprobe")
            self._ffprobe_cmd = ffprobe_path or "ffprobe"
            logger.info(f"Found ffmpeg via PATH: {ffmpeg_in_path}")
            return True

        self._ffmpeg_available = False
        logger.error("FFmpeg not found. Install: https://ffmpeg.org/download.html")
        return False

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration via ffprobe."""
        try:
            probe = subprocess.run(
                [self._ffprobe_cmd, "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                 str(audio_path)],
                capture_output=True, text=True, timeout=30,
            )
            if probe.returncode == 0 and probe.stdout.strip():
                return float(probe.stdout.strip())
        except Exception as e:
            logger.warning(f"ffprobe failed: {e}")
        return 55.0

    def _apply_captions(self, base_video: str, subtitle_path: str, output_path: str) -> bool:
        """
        Burn ASS subtitles directly into video frames using FFmpeg's ass filter.

        Unlike soft subtitles (which require users to manually enable CC),
        this hardcodes captions into the video so they're ALWAYS visible
        — matching the TikTok/Reels/Shorts caption style.
        """
        sub_path = Path(subtitle_path)
        if not sub_path.exists() or sub_path.stat().st_size < 50:
            logger.warning(f"  Subtitle file missing or too small: {subtitle_path}")
            return False

        # Validate ASS content
        try:
            content = sub_path.read_text(encoding="utf-8")
            if "[Events]" not in content or "Dialogue:" not in content:
                logger.warning("  Subtitle file missing valid ASS events")
                return False
        except Exception as e:
            logger.warning(f"  Subtitle file read error: {e}")
            return False

        sub_abs = str(sub_path.resolve())
        logger.info(f"  Hardcoding captions via ASS filter: {subtitle_path}")

        # Escape path for FFmpeg filter chain
        # On macOS/Linux, escape colons and single quotes, then wrap in single quotes
        safe_path = sub_abs.replace("'", "'\\''")
        ass_filter = f"ass='{safe_path}'"

        try:
            cmd = [
                self._ffmpeg_cmd, "-y",
                "-i", base_video,
                "-vf", ass_filter,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "copy",
                "-movflags", "+faststart",
                str(Path(output_path).resolve()),
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                stderr = result.stderr.decode()[:500]
                logger.warning(f"  ASS burn-in failed: {stderr}")
                return False

            if not Path(output_path).exists():
                logger.error("  Output file not created after caption burn")
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.error("  ASS burn-in timed out after 300s")
            return False
        except Exception as e:
            logger.error(f"  ASS burn-in error: {e}")
            return False

    async def assemble(self, state: dict) -> dict:
        audio_path = state.get("audio_path", "")
        thumbnail_path = state.get("thumbnail_url", "")
        subtitle_path = state.get("subtitle_path", "")

        if not audio_path or not Path(audio_path).exists():
            logger.warning("No audio file found, skipping video assembly")
            return {**state, "video_path": "", "current_step": "uploader"}

        if not self._check_ffmpeg():
            logger.error("FFmpeg not available, skipping video assembly")
            return {**state, "video_path": "", "current_step": "uploader"}

        logger.info(f"Assembling Shorts video ({self.WIDTH}x{self.HEIGHT})...")
        if subtitle_path:
            logger.info(f"Subtitles: {subtitle_path}")

        output_path = str(self.output_dir / f"short_{state.get('run_id', 'default')}.mp4")

        success = self._ffmpeg_assemble(audio_path, thumbnail_path, output_path, subtitle_path)

        if success:
            logger.info(f"Video: {output_path}")
        else:
            logger.error("FFmpeg assembly failed")

        return {**state, "video_path": output_path if success else "", "current_step": "uploader"}

    def _ffmpeg_assemble(self, audio: str, thumbnail: str, output: str, subtitle_path: str = "") -> bool:
        try:
            audio_path = Path(audio)
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio}")
                return False

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            duration = self._get_audio_duration(audio_path)
            if duration > 59:
                duration = 59

            logger.info(f"  Audio duration: {duration:.1f}s")

            # Step 1: Create base video (thumbnail + audio) — no subtitles
            base_video = str(output_path.with_suffix(".base.mp4"))
            has_thumbnail = thumbnail and Path(thumbnail).exists()

            if has_thumbnail:
                thumb_path = Path(thumbnail).resolve()
                cmd = [
                    self._ffmpeg_cmd, "-y",
                    "-loop", "1", "-i", str(thumb_path),
                    "-i", str(audio_path.resolve()),
                    "-vf",
                    f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,"
                    f"pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                    f"format=yuv420p",
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-tune", "stillimage",
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", str(duration),
                    "-r", "30",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    base_video,
                ]
            else:
                cmd = [
                    self._ffmpeg_cmd, "-y",
                    "-f", "lavfi", "-i",
                    f"color=c=0x0F0F19:s={self.WIDTH}x{self.HEIGHT}:d={duration}",
                    "-i", str(audio_path.resolve()),
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    base_video,
                ]

            logger.info("  Creating base video (thumbnail + audio)...")
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"FFmpeg base video failed: {result.stderr.decode()[:500]}")
                return False

            if not Path(base_video).exists():
                logger.error("Base video not created")
                return False

            # Step 2: Burn subtitles directly into video frames (always visible, TikTok-style)
            if subtitle_path and Path(subtitle_path).exists():
                caption_applied = self._apply_captions(base_video, subtitle_path, output_path)
                if caption_applied:
                    os.unlink(base_video)
                    logger.info("  ✅ Live captions burned into video — always visible")
                    return Path(output).exists()
                else:
                    logger.warning("  Caption burn failed, falling back to base video without captions")
                    os.rename(base_video, str(output_path))
                    return Path(output).exists()
            else:
                # No subtitles, just rename base video to final output
                os.rename(base_video, str(output_path))
                return Path(output).exists()

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out after 300s")
            return False
        except FileNotFoundError:
            logger.error("FFmpeg not found")
            return False
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            return False
