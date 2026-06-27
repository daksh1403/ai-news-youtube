import subprocess
import logging
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
            Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe",
            Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
            Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
            Path(r"C:\tools\ffmpeg\bin\ffmpeg.exe"),
            Path.home() / "scoop/shims/ffmpeg.exe",
            Path.home() / "ffmpeg/bin/ffmpeg.exe",
        ]
        for ffmpeg_path in search_paths:
            if ffmpeg_path.exists():
                self._ffmpeg_available = True
                self._ffmpeg_cmd = str(ffmpeg_path)
                self._ffprobe_cmd = str(ffmpeg_path.parent / "ffprobe.exe")
                return True

        self._ffmpeg_available = False
        logger.error("FFmpeg not found. Install: https://ffmpeg.org/download.html or winget install Gyan.FFmpeg")
        return False

    async def assemble(self, state: dict) -> dict:
        audio_path = state.get("audio_path", "")
        thumbnail_path = state.get("thumbnail_url", "")
        subtitle_path = state.get("subtitle_path", "")
        script = state.get("script", {})

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

            probe = subprocess.run(
                [self._ffprobe_cmd, "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                capture_output=True, text=True, timeout=30,
            )
            duration = float(probe.stdout.strip()) if probe.stdout.strip() else 55

            if duration > 59:
                duration = 59

            # Build video filter chain
            vfilters = []

            if thumbnail and Path(thumbnail).exists():
                thumb_path = Path(thumbnail).resolve()

                # Ken Burns effect: slow zoom from 100% to 105% over the duration
                # This makes the static thumbnail feel alive
                vfilters.append(
                    f"scale=2160:3840,zoompan=z='min(zoom+0.0005,1.05)':d={int(duration*30)}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.WIDTH}x{self.HEIGHT}:fps=30"
                )
                vfilters.append(f"format=yuv420p")

                # Burn live captions (ASS or SRT subtitle file)
                if subtitle_path and Path(subtitle_path).exists():
                    sub_resolved = str(Path(subtitle_path).resolve()).replace("\\", "/")
                    # Escape colons for ffmpeg filter syntax (Windows paths)
                    sub_resolved = sub_resolved.replace(":", "\\:")
                    vfilters.append(f"ass='{sub_resolved}'")
                    logger.info(f"Burning live captions: {subtitle_path}")

                vfilter_str = ",".join(vfilters)
                filter_complex = (
                    f"[0:v]{vfilter_str}[v];"
                    f"[1:a]aresample=44100[a]"
                )
                cmd = [
                    self._ffmpeg_cmd, "-y",
                    "-loop", "1", "-i", str(thumb_path), "-i", str(audio_path.resolve()),
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", str(duration),
                    "-r", "30",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(output_path),
                ]
            else:
                cmd = [
                    self._ffmpeg_cmd, "-y",
                    "-f", "lavfi", "-i", f"color=c=0x0F0F19:s={self.WIDTH}x{self.HEIGHT}:d={duration}",
                    "-i", str(audio_path.resolve()),
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    str(output_path),
                ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode()[:500]}")
            return result.returncode == 0 and Path(output).exists()

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out after 300s")
            return False
        except FileNotFoundError:
            logger.error("FFmpeg not found")
            return False
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            return False
