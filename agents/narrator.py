import subprocess
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# Best-sounding edge-tts voices (professional, clear, authoritative)
VOICE_OPTIONS = {
    "professional_male": "en-US-ChristopherNeural",
    "authoritative_male": "en-US-GuyNeural",
    "warm_female": "en-US-JennyNeural",
    "news_anchor_male": "en-US-BrandonNeural",
    "energetic_male": "en-US-DavisNeural",
    "default": "en-US-ChristopherNeural",
}


class NarrationAgent:
    def __init__(self, engine: str = "edge-tts", voice: str = "en-US-ChristopherNeural"):
        self.engine = engine
        # Resolve friendly voice names
        self.voice = VOICE_OPTIONS.get(voice, voice)
        self.output_dir = Path("output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def narrate(self, state: dict) -> dict:
        script = state.get("script", {})
        text = script.get("full_script", "")

        if not text:
            logger.warning("No script to narrate")
            return {**state, "audio_path": "", "subtitle_path": "", "current_step": "video"}

        text = text[:5000]
        run_id = state.get("run_id", "default")

        logger.info(f"Generating speech ({len(text)} chars) — voice: {self.voice}...")

        audio_path = str(self.output_dir / f"narration_{run_id}.mp3")
        ass_path = str(self.output_dir / f"narration_{run_id}.ass")

        # Try edge-tts first (generates audio + ASS word-by-word captions)
        subtitle_path = await self._edge_tts(text, audio_path, ass_path)

        if Path(audio_path).exists():
            logger.info(f"Audio: {audio_path}")
            if subtitle_path:
                logger.info(f"Live captions: {subtitle_path}")
            return {
                **state,
                "audio_path": audio_path,
                "subtitle_path": subtitle_path,
                "current_step": "video",
            }

        # Fallback to gTTS (no captions)
        logger.warning("edge-tts failed, trying gTTS fallback...")
        if self._gtts_fallback(text, audio_path):
            logger.info(f"Audio (gTTS): {audio_path}")
            return {
                **state,
                "audio_path": audio_path,
                "subtitle_path": "",
                "current_step": "video",
            }

        logger.error("All TTS engines failed")
        return {
            **state,
            "audio_path": "",
            "subtitle_path": "",
            "current_step": "video",
        }

    async def _edge_tts(self, text: str, output_path: str, ass_path: str = "") -> str:
        """Generate audio and ASS subtitles. Returns subtitle path or empty string."""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)

            # Collect word-level timing data for live captions
            word_timings = []

            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        word_timings.append({
                            "text": chunk["text"],
                            "offset": chunk["offset"],
                            "duration": chunk["duration"],
                        })

            if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
                return ""

            # Build ASS subtitle from word timings (one word at a time = live captions)
            if word_timings and ass_path:
                ass_content = self._build_ass(word_timings)
                if ass_content:
                    Path(ass_path).write_text(ass_content, encoding="utf-8")
                    logger.info(f"Generated {len(word_timings)} word-level caption events")
                    return ass_path

            return ""

        except ImportError:
            logger.warning("edge-tts not installed. Run: pip install edge-tts")
            return ""
        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            return ""

    def _build_ass(self, word_timings: list) -> str:
        """Build ASS subtitle with one word per event for live/karaoke-style captions.

        Each word appears centered on screen in large bold white text with black outline,
        matching the modern Shorts/Reels/TikTok caption style.
        """
        header = """[Script Info]
Title: Live Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,5,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        for timing in word_timings:
            word = timing["text"]
            if not word.strip():
                continue

            start_ass = self._ticks_to_ass_time(timing["offset"])
            end_ass = self._ticks_to_ass_time(timing["offset"] + timing["duration"])

            # Bold the word, add a subtle fade-in effect
            dialogue = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{{\\fad(40,40)}}{word}"
            events.append(dialogue)

        return header + "\n".join(events) + "\n"

    @staticmethod
    def _ticks_to_ass_time(ticks: int) -> str:
        """Convert 100-nanosecond ticks to ASS timestamp H:MM:SS.CC"""
        total_ms = ticks // 10_000
        cs = (total_ms % 1000) // 10  # centiseconds
        total_sec = total_ms // 1000
        sec = total_sec % 60
        total_min = total_sec // 60
        minute = total_min % 60
        hour = total_min // 60
        return f"{hour}:{minute:02d}:{sec:02d}.{cs:02d}"

    def _gtts_fallback(self, text: str, output_path: str) -> bool:
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang="en")
            tts.save(output_path)
            return Path(output_path).exists() and Path(output_path).stat().st_size > 0
        except ImportError:
            logger.warning("gTTS not installed. Run: pip install gTTS")
            return False
        except Exception as e:
            logger.error(f"gTTS error: {e}")
            return False

    def _piper_tts(self, text: str, output_path: str) -> bool:
        try:
            piper_path = os.getenv("PIPER_PATH", "piper")
            result = subprocess.run(
                [piper_path, "--model", "en_US-amy-medium", "--output_file", output_path],
                input=text.encode(),
                capture_output=True,
                timeout=120,
            )
            return result.returncode == 0 and Path(output_path).exists()
        except FileNotFoundError:
            logger.warning("Piper not found")
            return False
        except Exception as e:
            logger.error(f"Piper error: {e}")
            return False
