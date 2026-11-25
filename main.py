"""
main.py
-------
YouTube Ders Notu Üreteci (Gemini 2.5 Native Multimodal Audio Mimarisi)

Kullanım:
  python main.py <YouTube_URL>

Örnek:
  python main.py "https://www.youtube.com/watch?v=s7wmiS2mSXY"
"""

import argparse
import logging
import sys
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

from src.extractor import get_video_audio
from src.summarizer import generate_notes_from_audio

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
    return safe[:max_len] if safe else "ders_notu"


def _save_output(content: str, video_id: str, output_dir: Path, title: str = "") -> Path:
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
        description="YouTube videolarından Gemini Native Audio ile otomatik ders notu üretici",
    )
    parser.add_argument("url", help="YouTube video URL'si")
    parser.add_argument("--gemini-model", default=None, dest="gemini_model", help="Kullanılacak model")
    parser.add_argument("--output", default="output", help="Çıktı klasörü (varsayılan: ./output)")
    parser.add_argument("--keep-audio", action="store_true", help="İndirilen ses dosyasını silme")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  🎓 YouTube Ders Notu Üreteci (Gemini Multimodal Audio)")
    print("=" * 60)
    print(f"  URL   : {args.url}")
    print(f"  Çıktı : ./{args.output}/")
    print("=" * 60 + "\n")

    # 1. Ses İndirme
    print("📥 Adım 1/2: Video sesi ayıklanıyor...")
    try:
        audio_info = get_video_audio(args.url)
    except Exception as e:
        logger.error(f"Ses indirilemedi: {e}")
        sys.exit(1)

    print(f"   ✅ Ses hazır: {Path(audio_info.audio_path).name} | Başlık: {audio_info.title}\n")

    # 2. Gemini Dinleme ve Ders Notu Üretimi
    print("🧠 Adım 2/2: Gemini videonun tam transkriptini ve ders notunu çıkarıyor...")
    try:
        notes = generate_notes_from_audio(
            audio_path=audio_info.audio_path,
            video_title=audio_info.title,
            model_name=args.gemini_model,
        )
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analiz hatası: {e}")
        sys.exit(1)

    # 3. Notu Kaydetme
    output_path = _save_output(
        content=notes,
        video_id=audio_info.video_id,
        output_dir=Path(args.output),
        title=audio_info.title,
    )

    # Geçici ses dosyasını temizle (istenirse)
    if not args.keep_audio:
        try:
            Path(audio_info.audio_path).unlink(missing_ok=True)
        except Exception:
            pass

    print("\n" + "=" * 60)
    print("  🎉 TEBRİKLER! DERS NOTU HAZIRLANDI!")
    print(f"  📄 Dosya: {output_path}")
    print("=" * 60 + "\n")

    print("--- ÜRETİLEN NOTUN İLK BÖLÜMÜ ---")
    print(notes[:500] + "\n...")


if __name__ == "__main__":
    main()
