"""
main.py
-------
Hibrit YouTube Toplantı & Ders Notu Üreteci:
1. Whisper AI: Videonun baştan sona birebir tam transkriptini (zaman damgalı) yerel olarak çıkarır.
2. Google Gemini: Bu transkriptten akademik kalitede ders notu, özet ve sınav soruları üretir.
"""

import argparse
import logging
import sys
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.extractor import download_audio, transcribe_audio_with_whisper
from src.summarizer import generate_study_notes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _safe_filename(text: str, max_len: int = 50) -> str:
    safe = re.sub(r'[^\w\s-]', '', text).strip()
    safe = re.sub(r'[\s]+', '_', safe)
    return safe[:max_len] if safe else "notlar"


def _save_output(content: str, output_dir: Path, title: str = "", video_id: str = "") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = _safe_filename(title) if title else video_id
    filename = f"{base}_{timestamp}.md"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        prog="yt-study-notes",
        description="Whisper (Tam Transkript) + Gemini (Ders Notu) Hibrit Asistan",
    )
    parser.add_argument("url", help="YouTube video URL'si")
    parser.add_argument("--whisper-model", default="base", help="Whisper model boyutu (varsayılan: base)")
    parser.add_argument("--gemini-model", default=None, help="Gemini model adı (varsayılan: .env)")
    parser.add_argument("--output", default="output", help="Çıktı klasörü (varsayılan: ./output)")
    parser.add_argument("--keep-audio", action="store_true", help="İndirilen ses dosyasını silme")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  🎓 YouTube Toplantı & Ders Notu Üreteci (Whisper + Gemini)")
    print("=" * 65)
    print(f"  URL   : {args.url}")
    print(f"  Çıktı : ./{args.output}/")
    print("=" * 65 + "\n")

    # 1. Ses İndirme (yt-dlp)
    print("📥 Adım 1/3: Video sesi ayıklanıyor...")
    try:
        video_id, title, duration_min, audio_path = download_audio(args.url)
    except Exception as e:
        logger.error(f"Ses indirilemedi: {e}")
        sys.exit(1)

    print(f"   ✅ Ses hazır: {Path(audio_path).name} | Başlık: {title}\n")

    # 2. Yerel Transkripsiyon (Whisper)
    print("🎙️ Adım 2/3: Whisper ile videonun baştan sona tam transkripti çıkarılıyor...")
    try:
        language, full_transcript, segments = transcribe_audio_with_whisper(
            audio_path=audio_path,
            model_size=args.whisper_model,
        )
    except Exception as e:
        logger.error(f"Whisper transkripsiyon hatası: {e}")
        sys.exit(1)

    print(f"   ✅ Transkript tamamlandı! Dil: {language.upper()} | Toplam {len(segments)} cümle\n")

    # 3. Ders Notu Üretimi (Gemini)
    print("🧠 Adım 3/3: Gemini transkripti inceliyor, ders notu ve özet hazırlanıyor...")
    try:
        study_notes = generate_study_notes(
            transcript_text=full_transcript,
            video_title=title,
            model_name=args.gemini_model,
        )
    except Exception as e:
        logger.error(f"Gemini analiz hatası: {e}")
        sys.exit(1)

    print("   ✅ Ders notları başarıyla oluşturuldu!\n")

    # 4. İki Bölümlü Tam Dokümanı Oluşturma
    document_content = f"""# 📚 {title}

---

# 🎙️ BÖLÜM 1: VİDEONUN BİREBİR TAM TRANSKRİPTİ (Whisper AI)
> **Kaynak Dil:** {language.upper()} | **Toplam Segment:** {len(segments)} | **Model:** Faster-Whisper ({args.whisper_model})

{full_transcript}

---

# 🎓 BÖLÜM 2: YAPAY ZEKA DERS NOTLARI VE ANALİZ (Google Gemini)

{study_notes}
"""

    output_path = _save_output(
        content=document_content,
        output_dir=Path(args.output),
        title=title,
        video_id=video_id,
    )

    # Geçici ses dosyasını temizle
    if not args.keep_audio:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass

    print("=" * 65)
    print("  🎉 TEBRİKLER! İŞLEM BAŞARIYLA TAMAMLANDI!")
    print(f"  📄 Dosya: {output_path}")
    print("=" * 65 + "\n")

    print("--- TRANSKRİPTTEN İLK KESİT ---")
    first_lines = "\n".join(full_transcript.splitlines()[:5])
    print(first_lines)
    print("...\n")


if __name__ == "__main__":
    main()
