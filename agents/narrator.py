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
            return {**state, "audio_path": "", "subtitle_path": "", "current_step": "narrator"}

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
                "current_step": "narrator",
            }

        # Fallback to gTTS (no captions)
        logger.warning("edge-tts failed, trying gTTS fallback...")
        if self._gtts_fallback(text, audio_path):
            logger.info(f"Audio (gTTS): {audio_path}")
            return {
                **state,
                "audio_path": audio_path,
                "subtitle_path": "",
                "current_step": "narrator",
            }

        logger.error("All TTS engines failed")
        return {
            **state,
            "audio_path": "",
            "subtitle_path": "",
            "current_step": "narrator",
        }

    async def _edge_tts(self, text: str, output_path: str, ass_path: str = "") -> str:
        """Generate audio and ASS subtitles. Returns subtitle path or empty string."""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)

            # Collect sentence-level timing data for synchronized captions
            sentence_timings = []
            audio_duration_ticks = 0

            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "SentenceBoundary":
                        sentence_timings.append({
                            "text": chunk["text"],
                            "offset": chunk["offset"],
                            "duration": chunk["duration"],
                        })
                        end_tick = chunk["offset"] + chunk["duration"]
                        if end_tick > audio_duration_ticks:
                            audio_duration_ticks = end_tick

            if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
                return ""

            # Build ASS subtitle from sentence timings (one sentence at a time = synchronized)
            if sentence_timings and ass_path:
                ass_content = self._build_ass(sentence_timings)
                if ass_content:
                    Path(ass_path).write_text(ass_content, encoding="utf-8")
                    logger.info(f"Generated {len(sentence_timings)} sentence-level caption events")
                    return ass_path

            # Fallback: if edge-tts didn't emit SentenceBoundary events,
            # create synthetic sentence timings by splitting text into sentences
            if not sentence_timings and ass_path:
                logger.info("No SentenceBoundary events from edge-tts — generating synthetic sentence timings")
                duration_ticks = audio_duration_ticks if audio_duration_ticks > 0 else 55_000_000
                synthetic = self._build_synthetic_timings(text, duration_ticks)
                if synthetic:
                    ass_content = self._build_ass(synthetic)
                    if ass_content:
                        Path(ass_path).write_text(ass_content, encoding="utf-8")
                        logger.info(f"Generated {len(synthetic)} synthetic sentence-level caption events")
                        return ass_path

            return ""

        except ImportError:
            logger.warning("edge-tts not installed. Run: pip install edge-tts")
            return ""
        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            return ""

    def _build_ass(self, timings: list) -> str:
        """Build ASS subtitle with sentence-level captions.

        Each sentence appears ONE AT A TIME, exactly when spoken.
        The current sentence is displayed centered on screen.
        When the next sentence starts, it replaces the previous one.
        This creates synchronized captions with the audio.
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
Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,5,30,30,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        if not timings:
            return ""

        events = []
        for timing in timings:
            text = timing["text"]
            if not text or not text.strip():
                continue

            start_tick = timing["offset"]
            end_tick = start_tick + timing["duration"]

            start_ass = self._ticks_to_ass_time(start_tick)
            end_ass = self._ticks_to_ass_time(end_tick)

            dialogue = f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}"
            events.append(dialogue)

        return header + "\n".join(events) + "\n"

    def _build_synthetic_timings(self, text: str, total_duration_ticks: int) -> list:
        """Generate synthetic sentence timings when edge-tts doesn't emit SentenceBoundary events.

        Splits the text into sentences and distributes them evenly across the audio duration.
        """
        import re
        # Split into sentences (handles . ! ? and line breaks)
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return []

        if total_duration_ticks <= 0:
            total_duration_ticks = 55_000_000

        per_sentence_ticks = total_duration_ticks // len(sentences)
        timings = []
        for i, sentence in enumerate(sentences):
            offset = i * per_sentence_ticks
            timings.append({
                "text": sentence,
                "offset": offset,
                "duration": per_sentence_ticks,
            })
        return timings

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
