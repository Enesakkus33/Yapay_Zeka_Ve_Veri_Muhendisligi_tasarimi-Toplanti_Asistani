"""
extractor.py
------------
1. yt-dlp ile YouTube videosunun sesini (MP3) indirir.
2. Yerel Whisper (Faster-Whisper) modeliyle videonun baştan sona
   birebir zaman damgalı tam transkriptini çıkarır.
"""

import os
import re
import time
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# --- MONKEYPATCH: PyAV metadata_errors hatasını engelle ---
try:
    import av
    _original_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _original_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass
# -----------------------------------------------------------


@dataclass
class TranscribeResult:
    video_id: str
    title: str
    audio_path: str
    duration_min: int
    language: str
    full_transcript_text: str
    segments: list[dict] # [{"start": float, "text": str}]


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


def download_audio(url: str, output_dir: Path | None = None) -> tuple[str, str, int, str]:
    """
    YouTube videosundan sesi indirir.
    Döner: (video_id, title, duration_min, audio_path)
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

    title = video_id
    duration = 0

    # Eğer ses zaten inmişse doğrudan kullan
    if audio_file.exists() and audio_file.stat().st_size > 10_000:
        logger.info(f"[Extractor] Ses önceden indirilmiş: {audio_file.name}")
        return video_id, title, duration, str(audio_file)

    logger.info(f"[Extractor] Ses indiriliyor → {url}")
    ydl_opts = {
        "format": "ba/b/bestaudio",
        "outtmpl": str(audio_file.with_suffix("")),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "96",
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

    logger.info(f"[Extractor] ✅ Ses indirildi: {audio_file.name} ({duration} dk)")
    return video_id, title, duration, str(audio_file)


def transcribe_audio_with_whisper(
    audio_path: str,
    model_size: str = "base",
) -> tuple[str, str, list[dict]]:
    """
    Faster-Whisper yerel modeliyle sesi baştan sona metne döker.
    Döner: (language, full_transcript_text, segments_list)
    """
    from faster_whisper import WhisperModel

    model_dir = Path(__file__).parent.parent / "models" / model_size
    model_target = str(model_dir) if model_dir.exists() and (model_dir / "model.bin").exists() else model_size

    # CPU (int8) - Windows ortamında son derece kararlı ve hızlı
    device = "cpu"
    compute_type = "int8"

    logger.info(f"[Whisper] 🎧 Model yükleniyor ({model_size} | {device.upper()})...")
    model = WhisperModel(model_target, device=device, compute_type=compute_type)

    logger.info(f"[Whisper] 🎙️ Ses metne dökülüyor ({Path(audio_path).name})...")
    t0 = time.time()
    segments_iter, info = model.transcribe(audio_path, beam_size=5)

    segments = []
    lines = []
    for seg in segments_iter:
        m, s = int(seg.start // 60), int(seg.start % 60)
        timestamp = f"[{m:02d}:{s:02d}]"
        clean_text = seg.text.strip()
        segments.append({"start": seg.start, "text": clean_text})
        lines.append(f"{timestamp} {clean_text}")

    full_text = "\n".join(lines)
    elapsed = time.time() - t0
    logger.info(f"[Whisper] ✅ Transkripsiyon tamamlandı! Dil: {info.language.upper()} | {len(segments)} segment | Süre: {elapsed:.2f} sn")

    return info.language, full_text, segments
