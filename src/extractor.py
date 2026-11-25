"""
extractor.py
------------
YouTube URL'sinden videonun sesini (MP3) en hızlı ve temiz şekilde indiren modül.
YouTube'un altyazı engellerini ve yerel Whisper hatalarını baypas eder.
"""

import os
import re
import logging
import tempfile
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    video_id: str
    title: str
    audio_path: str
    duration_min: int


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Geçerli bir YouTube URL'si bulunamadı: {url}")


def get_video_audio(url: str, output_dir: Path | None = None) -> AudioResult:
    """
    YouTube videosunun sesini indirir ve yerel MP3 yolunu döner.
    Android istemcisi kullandığı için YouTube 403 engeli vermez.
    """
    import yt_dlp

    video_id = extract_video_id(url)
    logger.info(f"[Extractor] Video ID: {video_id}")

    if output_dir is None:
        target_dir = Path(__file__).parent.parent / "temp_audio"
    else:
        target_dir = output_dir

    target_dir.mkdir(parents=True, exist_ok=True)
    audio_file = target_dir / f"{video_id}.mp3"

    # Eğer daha önce indirilmişse tekrar indirme
    if audio_file.exists() and audio_file.stat().st_size > 10_000:
        logger.info(f"[Extractor] Ses zaten mevcut: {audio_file.name}")
        return AudioResult(video_id=video_id, title=video_id, audio_path=str(audio_file), duration_min=0)

    logger.info(f"[Extractor] Ses indiriliyor → {url}")

    ydl_opts = {
        "format": "ba/b/bestaudio",
        "outtmpl": str(audio_file.with_suffix("")),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "96", # Hızlı yükleme ve Gemini analizi için ideal kalite
        }],
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", video_id)
        duration = info.get("duration", 0) // 60

    logger.info(f"[Extractor] ✅ Ses hazır: {audio_file.name} ({duration} dk)")
    return AudioResult(
        video_id=video_id,
        title=title,
        audio_path=str(audio_file),
        duration_min=duration,
    )
