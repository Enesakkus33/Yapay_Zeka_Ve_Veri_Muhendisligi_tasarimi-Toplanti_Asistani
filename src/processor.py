"""
processor.py
------------
Ham transkripti temizleme ve LLM'e gönderilmek üzere anlamlı parçalara (chunk) bölme.

Neden chunk'lama?
  - Kısa videolarda (<30dk) tüm transkript tek LLM çağrısına sığar.
  - Uzun videolarda (>30dk) tek seferde gönderme context limit'i aşabilir.
    Bu durumda kelime bazlı chunk'lama devreye girer.
"""

import re
import logging
from dataclasses import dataclass
from src.extractor import TranscriptResult

logger = logging.getLogger(__name__)

# Chunk başına maksimum kelime sayısı (Gemini 2.5 Flash için güvenli sınır)
DEFAULT_MAX_WORDS_PER_CHUNK = 12_000


@dataclass
class ProcessedTranscript:
    video_id: str
    language: str
    source: str
    full_text: str            # Tüm transkript (referans için)
    chunks: list[str]         # LLM'e gönderilecek parçalar
    is_chunked: bool          # True ise birden fazla chunk var


def _clean_text(text: str) -> str:
    """
    Transkript metnini temizler:
    - Tekrarlayan boşlukları/satır sonlarını birleştirir
    - [müzik], [alkış] gibi ses etiketlerini kaldırır
    - Baştaki/sondaki boşlukları temizler
    """
    # Ses/efekt etiketlerini kaldır: [music], [applause], [müzik] vb.
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)  # (müzik) formatı

    # Birden fazla boşluğu tek boşluğa indir
    text = re.sub(r"[ \t]+", " ", text)

    # Üçten fazla art arda satır sonunu iki satır sonuna indir
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _segments_to_text(segments: list[dict], include_timestamps: bool = True) -> str:
    """
    Segment listesini okunabilir metin bloğuna dönüştürür.

    Args:
        segments: [{"start": float, "text": str}, ...]
        include_timestamps: True ise her cümle başına [dk:sn] ekler

    Returns:
        Birleştirilmiş metin
    """
    lines = []
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        if include_timestamps:
            start_sec = int(seg["start"])
            minutes, seconds = divmod(start_sec, 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            lines.append(f"{timestamp} {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def _split_into_chunks(text: str, max_words: int) -> list[str]:
    """
    Metni kelime sınırlarına göre eşit parçalara böler.
    Cümle ortasında kesmemek için en yakın nokta/satır sonunu bulur.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end

    logger.info(f"[Processor] Metin {len(chunks)} chunk'a bölündü (maks {max_words} kelime/chunk)")
    return chunks


def process(
    transcript: TranscriptResult,
    max_words_per_chunk: int = DEFAULT_MAX_WORDS_PER_CHUNK,
    include_timestamps: bool = True,
) -> ProcessedTranscript:
    """
    TranscriptResult'ı alır, temizler ve chunk'lara böler.

    Args:
        transcript: extractor.get_transcript() çıktısı
        max_words_per_chunk: Her chunk'taki maksimum kelime sayısı
        include_timestamps: Zaman damgaları eklensin mi?

    Returns:
        ProcessedTranscript nesnesi
    """
    logger.info(f"[Processor] İşleniyor | kaynak: {transcript.source} | {len(transcript.segments)} segment")

    raw_text = _segments_to_text(transcript.segments, include_timestamps=include_timestamps)
    clean_text = _clean_text(raw_text)

    word_count = len(clean_text.split())
    logger.info(f"[Processor] Toplam kelime sayısı: {word_count:,}")

    chunks = _split_into_chunks(clean_text, max_words_per_chunk)

    return ProcessedTranscript(
        video_id=transcript.video_id,
        language=transcript.language,
        source=transcript.source,
        full_text=clean_text,
        chunks=chunks,
        is_chunked=len(chunks) > 1,
    )
